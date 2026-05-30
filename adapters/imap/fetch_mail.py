#!/usr/bin/env python3
"""Liest die E-Mails der letzten 24 Stunden aus allen relevanten Ordnern und
gibt sie als JSON auf stdout aus. Markiert NICHTS als gelesen (BODY.PEEK) und
veraendert das Postfach nicht.

Gescannt werden: INBOX und alle Unterordner (server-seitige Filter sortieren
viele Mails direkt in Unterordner). Spam wird mitgelesen und mit
`is_spam: true` markiert -- nuetzlich, um False-Positives zu finden; es wird
aber nichts automatisch aus Spam herausgeholt. Uebersprungen werden Papierkorb,
Entwuerfe, Gesendet und das System-Archiv.
"""

import email
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _imap_common import (  # noqa: E402
    load_config, connect_imap, die, imap_utf7_decode,
)

LOOKBACK_HOURS = 24
MAX_BODY_CHARS = 4000


class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html):
    if not html:
        return ""
    p = _Stripper()
    try:
        p.feed(html)
        text = "".join(p.parts)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def decode_header_value(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def decode_part(part):
    try:
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
    except Exception:
        return ""


def extract_body(msg):
    text, html = None, None
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            disposition = str(part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            ctype = part.get_content_type()
            if ctype == "text/plain" and text is None:
                text = decode_part(part)
            elif ctype == "text/html" and html is None:
                html = decode_part(part)
    else:
        payload = decode_part(msg)
        if msg.get_content_type() == "text/html":
            html = payload
        else:
            text = payload
    body = text if (text and text.strip()) else html_to_text(html)
    return (body or "").strip()[:MAX_BODY_CHARS]


# DMARC/SPF/DKIM aus den Authentication-Results-Headern, die der empfangende
# Server gesetzt hat. Der Wert ist das Pruef-Ergebnis (pass/fail/none/softfail/
# ...), nicht die Policy. Fehlt der Header (manche IMAP-Server setzen ihn nicht),
# ist das Ergebnis "unbekannt" -- das ist KEIN Verdacht.
_AUTH_METHOD_RE = re.compile(r"\b(dmarc|spf|dkim)\s*=\s*([A-Za-z]+)", re.I)


def _agg(vals):
    """Mehrere Ergebnisse einer Methode zusammenfassen: 'pass' schlaegt alles,
    danach 'fail'; sonst der erste Wert."""
    if not vals:
        return None
    low = [v.lower() for v in vals]
    if "pass" in low:
        return "pass"
    if "fail" in low:
        return "fail"
    return low[0]


def extract_auth(msg):
    headers = msg.get_all("Authentication-Results") or []
    if not headers:
        return None
    found = {"dmarc": [], "spf": [], "dkim": []}
    for h in headers:
        for m in _AUTH_METHOD_RE.finditer(h):
            found[m.group(1).lower()].append(m.group(2))
    dmarc, spf, dkim = _agg(found["dmarc"]), _agg(found["spf"]), _agg(found["dkim"])

    # Verdict konservativ -- lieber unter- als ueberflaggen:
    #  - "suspicious": DMARC schlaegt fehl, oder SPF UND DKIM versagen beide.
    #  - "weak": kein starker Pass und Signale fehlen/none (z. B. Domain ohne
    #    DMARC-Record) -> im Briefing nur leise erwaehnen.
    #  - "pass": mindestens ein starkes Signal besteht.
    #  - "unknown": nichts Belastbares (sollte mit Header selten sein).
    spf_bad = spf in ("fail", "softfail", "none", None)
    dkim_bad = dkim in ("fail", "none", None)
    if dmarc == "fail" or (spf == "fail" and dkim_bad):
        verdict = "suspicious"
    elif dmarc == "pass" or spf == "pass" or dkim == "pass":
        verdict = "pass"
    elif dmarc in ("none", None) and spf_bad and dkim_bad:
        verdict = "weak"
    else:
        verdict = "unknown"

    return {"dmarc": dmarc, "spf": spf, "dkim": dkim, "verdict": verdict}


# Primaere Erkennung: SPECIAL-USE-Flags (sprachunabhaengig, RFC 6154).
# \All/\Important sind Gmails virtuelle Sammelordner ("All Mail", "Wichtig") --
# sie duplizieren jede Mail und werden uebersprungen, sonst Mehrfach-Scan.
SKIP_FLAGS = ("\\Trash", "\\Drafts", "\\Sent", "\\Archive", "\\All", "\\Important")
# Fallback-Namensliste fuer Server, die keine SPECIAL-USE-Flags setzen.
# Bewusst OHNE "archiv"/"archive"-Eigenname-Varianten, die User fuer echte Mail
# nutzen -- "Archiv" wird NUR ueber das \Archive-Flag uebersprungen, nie ueber
# den Namen. Spam ebenfalls nicht hier (wird gelesen + als is_spam markiert).
SKIP_NAMES = {
    "sent", "gesendet", "gesendete objekte", "gesendete elemente",
    "sent messages", "sent items",
    "drafts", "entwurf", "entw\xfcrfe",
    "trash", "papierkorb",
    "deleted", "deleted items", "deleted messages",
    "gel\xf6schte objekte", "gel\xf6schte elemente",
}

# LIST-Antwort: (flags) "DELIM" "Name"  -- Trennzeichen ist server-spezifisch
# ("/" bei 1und1, "." bei vielen Dovecot-Servern, NIL ohne Hierarchie). Wir
# lesen es aus der Antwort, statt "/" anzunehmen.
_LIST_RE = re.compile(
    r'\((?P<flags>[^)]*)\)\s+'
    r'(?:"(?P<delim>(?:[^"\\]|\\.)*)"|(?P<delim2>NIL|\S+))\s+'
    r'(?:"(?P<name>(?:[^"\\]|\\.)*)"|(?P<name2>.+?))\s*$'
)


def _list_folders(conn):
    typ, data = conn.list()
    if typ != "OK":
        return []
    out = []
    for b in data or []:
        if b is None:
            continue
        line = b.decode(errors="replace")
        m = _LIST_RE.match(line)
        if not m:
            continue
        name = m.group("name")
        if name is not None:
            name = name.replace('\\"', '"').replace("\\\\", "\\")
        else:
            name = m.group("name2")
        if not name:
            continue
        out.append((name, m.group("flags") or ""))
    return out


def _should_skip(name, flags):
    if any(f in flags for f in SKIP_FLAGS):
        return True
    # Trennzeichen ist server-abhaengig; auf "/" UND "." segmentieren und den
    # obersten Ordner + Blatt-Namen gegen die System-Namensliste pruefen.
    segs = [s.strip().lower() for s in re.split(r"[/.]", name) if s.strip()]
    if segs and (segs[-1] in SKIP_NAMES or segs[0] in SKIP_NAMES):
        return True
    return False


def _is_spam(name, flags):
    return "\\Junk" in flags or name.lower() == "spam"


def main():
    cfg = load_config()
    # Zeitfenster an die Lauf-Frequenz anpassen (z. B. stündlich -> 1).
    # Quelle: config.json "lookback_hours" oder ENV MAIL_LOOKBACK_HOURS, sonst 24.
    try:
        lookback = float(os.environ.get("MAIL_LOOKBACK_HOURS")
                         or cfg.get("lookback_hours") or LOOKBACK_HOURS)
    except (TypeError, ValueError):
        lookback = LOOKBACK_HOURS
    since = datetime.now(timezone.utc) - timedelta(hours=lookback)
    # IMAP SINCE arbeitet tagesgenau -> einen Tag weiter zurueck suchen,
    # danach exakt nach Zeitstempel filtern.
    since_imap = (since - timedelta(days=1)).strftime("%d-%b-%Y")

    conn = connect_imap(cfg)
    try:
        folders = _list_folders(conn)
    except Exception as e:
        die(f"Ordnerliste konnte nicht gelesen werden: {e}")

    by_key = {}
    for name, flags in folders:
        dname = imap_utf7_decode(name)  # lesbar fuer Anzeige/Skip-Check
        if _should_skip(dname, flags):
            continue
        is_spam = _is_spam(dname, flags)
        # Reconnect pro Ordner: ein fehlschlagendes SELECT (z. B. exotische
        # Sonderzeichen) kann die Session abreissen.
        try:
            conn.logout()
        except Exception:
            pass
        conn = connect_imap(cfg)
        try:
            st, _ = conn.select('"%s"' % name, readonly=True)
            if st != "OK":
                continue
            typ, data = conn.uid("search", None, f"(SINCE {since_imap})")
            if typ != "OK":
                continue
            uids = data[0].split()
        except Exception:
            continue
        for uid in uids:
            try:
                typ, msg_data = conn.uid("fetch", uid, "(BODY.PEEK[])")
            except Exception:
                break
            if typ != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            dt = None
            try:
                dt = parsedate_to_datetime(msg.get("Date"))
                if dt is not None and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                dt = None
            if dt is None or dt < since:
                continue
            mid = (msg.get("Message-ID") or "").strip()
            entry = {
                "uid": uid.decode(),
                "folder": dname,
                "is_spam": is_spam,
                "message_id": mid,
                "in_reply_to": (msg.get("In-Reply-To") or "").strip(),
                "references": (msg.get("References") or "").strip(),
                "from": decode_header_value(msg.get("From")),
                "to": decode_header_value(msg.get("To")),
                "subject": decode_header_value(msg.get("Subject")),
                "date": dt.isoformat() if dt else (msg.get("Date") or ""),
                "auth": extract_auth(msg),
                "body": extract_body(msg),
            }
            key = mid or f"_nomid::{dname}::{uid.decode()}"
            existing = by_key.get(key)
            if existing is None or (existing.get("is_spam") and not is_spam):
                by_key[key] = entry
    try:
        conn.logout()
    except Exception:
        pass

    emails = sorted(by_key.values(), key=lambda x: x.get("date", ""),
                    reverse=True)
    print(json.dumps({"count": len(emails), "emails": emails},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
