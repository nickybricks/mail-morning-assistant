#!/usr/bin/env python3
"""Holt gezielt nur die AI-Newsletter (config 'ai_digest_senders') der letzten N
Stunden ueber die Gmail-REST-API (HTTPS) und gibt sie gekuerzt als JSON aus —
Grundlage fuer die separate AI-Digest-Mail (siehe core/briefing.md, Abschnitt
"AI-Digest"). Veraendert das Postfach NICHT (nur Lesezugriffe).

Anders als fetch_mail.py zieht dieses Skript nicht das ganze Postfach, sondern
filtert per Gmail-Query auf die Digest-Sender und kuerzt jeden Body — so bleibt
der taegliche Cloud-Lauf klein und guenstig.

Funktioniert im claude.ai-Cloud-Environment (nur 443/HTTPS), wo IMAP gesperrt ist.

Aufruf:  python3 fetch_digest.py
ENV/Config:
- ai_digest_senders        (config.json, Pflicht): Liste Domains/Adressen
- ai_digest_window_hours   (config.json, Default 24) oder ENV MAIL_DIGEST_WINDOW_HOURS
- MAIL_DIGEST_BODY_CHARS   (ENV, Default 12000): max. Zeichen pro Body-Excerpt
"""
import base64
import email
import json
import math
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _gmail_common import load_config, access_token, api, die  # noqa: E402
from _mime import decode_header_value, decode_part, html_to_text  # noqa: E402

WINDOW_HOURS = 24
# Hoeher als _mime.MAX_BODY_CHARS (4000): der Digest soll vollstaendig sein,
# nicht nur die erste Meldung. Pro Body, ueber ENV MAIL_DIGEST_BODY_CHARS steuerbar.
BODY_CHARS = 12000


def extract_full_body(msg):
    """Wie _mime.extract_body, aber OHNE 4000-Cap und nimmt den *reicheren* von
    text/plain vs. text/html — manche Newsletter haben nur einen Plain-Teaser,
    der eigentliche Inhalt steckt im HTML."""
    text, html = None, None
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if "attachment" in str(part.get("Content-Disposition") or "").lower():
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
    plain = (text or "").strip()
    from_html = html_to_text(html) if html else ""
    # Den laengeren/inhaltsreicheren Body nehmen.
    return plain if len(plain) >= len(from_html) else from_html


def clean_invisibles(text):
    """Unsichtbare Fueller raus, die Newsletter massenhaft als Preheader-Spacer
    einstreuen (Zero-Width-Space, ZWNJ/ZWJ, Bidi-/Format-Steuerzeichen, BOM,
    Soft-Hyphen ...). Non-Breaking-/Spezial-Leerzeichen -> normales Leerzeichen.
    Kategorie-basiert via unicodedata, damit kein literales Sonderzeichen im
    Quelltext stehen muss."""
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat == "Cf":            # Format-Zeichen (ZWSP, ZWNJ, LRM, BOM, SHY ...)
            continue
        if cat == "Zs" and ch != " ":  # alle Nicht-Standard-Leerzeichen (NBSP ...)
            out.append(" ")
            continue
        out.append(ch)
    return "".join(out)


def trim_body(text, limit):
    """Unsichtbare Fueller entfernen, Whitespace zusammenfassen, auf 'limit' kuerzen."""
    if not text:
        return "", False
    text = clean_invisibles(text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= limit:
        return text, False
    return text[:limit].rstrip() + "\n…[gekuerzt]", True


def list_ids(token, query):
    ids, page = [], None
    while True:
        params = {"q": query, "maxResults": 500}
        if page:
            params["pageToken"] = page
        resp = api("GET", "/messages", token, params=params)
        ids.extend(m["id"] for m in resp.get("messages", []))
        page = resp.get("nextPageToken")
        if not page:
            return ids


def fetch_raw(token, msg_id):
    resp = api("GET", f"/messages/{msg_id}", token, params={"format": "raw"})
    raw = base64.urlsafe_b64decode(resp["raw"].encode())
    return email.message_from_bytes(raw), resp.get("threadId")


def main():
    cfg = load_config()
    senders = cfg.get("ai_digest_senders") or []
    if not senders:
        die("config.json: 'ai_digest_senders' ist leer — kein AI-Digest zu bauen.")

    try:
        window = float(os.environ.get("MAIL_DIGEST_WINDOW_HOURS")
                       or cfg.get("ai_digest_window_hours") or WINDOW_HOURS)
    except (TypeError, ValueError):
        window = WINDOW_HOURS
    try:
        body_chars = int(os.environ.get("MAIL_DIGEST_BODY_CHARS") or BODY_CHARS)
    except (TypeError, ValueError):
        body_chars = BODY_CHARS

    token = access_token(cfg["email"])

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=window)
    # Gmail newer_than ist tagesgenau -> weiter zurueck suchen, dann exakt filtern.
    days_wide = int(math.ceil(window / 24)) + 1

    from_clause = " OR ".join(f"from:{s}" for s in senders)
    # Spam/Trash standardmaessig aus; Digest-Sender sind abonniert.
    query = f"newer_than:{days_wide}d ({from_clause})"

    try:
        ids = list_ids(token, query)
    except SystemExit:
        raise
    except Exception as e:
        die(f"Gmail-Suche fehlgeschlagen: {e}")

    editions, truncated_any = [], False
    for mid_g in ids:
        try:
            msg, thread_id = fetch_raw(token, mid_g)
        except SystemExit:
            raise
        except Exception:
            continue
        try:
            dt = parsedate_to_datetime(msg.get("Date"))
            if dt is not None and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            dt = None
        if dt is None or dt < since:
            continue
        body, was_trimmed = trim_body(extract_full_body(msg), body_chars)
        truncated_any = truncated_any or was_trimmed
        editions.append({
            "uid": mid_g,
            "thread_id": thread_id,
            "from": decode_header_value(msg.get("From")),
            "subject": decode_header_value(msg.get("Subject")),
            "date": dt.isoformat(),
            "body_excerpt": body,
        })

    editions.sort(key=lambda x: x.get("date", ""), reverse=True)
    print(json.dumps({
        "count": len(editions),
        "window_hours": window,
        "body_char_limit": body_chars,
        "any_truncated": truncated_any,
        "editions": editions,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
