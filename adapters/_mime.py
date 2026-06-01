"""Adapter-agnostisches RFC822-MIME-Parsing — gemeinsam genutzt von IMAP- und
Gmail-REST-Adapter (beide bekommen rohe MIME-Bytes und brauchen identische
Body-Extraktion, Header-Dekodierung und DMARC/SPF/DKIM-Auswertung). Stdlib only.
"""
import re
from email.header import decode_header, make_header
from html.parser import HTMLParser

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
# ...), nicht die Policy. Fehlt der Header (manche Server setzen ihn nicht),
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
