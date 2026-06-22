"""Adapter-agnostisches RFC822-MIME-Parsing — gemeinsam genutzt von IMAP- und
Gmail-REST-Adapter (beide bekommen rohe MIME-Bytes und brauchen identische
Body-Extraktion, Header-Dekodierung und DMARC/SPF/DKIM-Auswertung). Stdlib only.
"""
import re
from email.header import decode_header, make_header
from html.parser import HTMLParser

MAX_BODY_CHARS = 4000


class _Stripper(HTMLParser):
    """HTML -> Text. Standardmaessig werden alle Tags verworfen (knapper Klartext
    fuers Haupt-Briefing). Mit keep_links/keep_images werden Links als
    [text](url) und Bilder als ![alt](url) eingebettet — gebraucht fuer den
    AI-Digest, wo der Nutzer Quellen-Links folgen und Bilder sehen koennen soll."""

    def __init__(self, keep_links=False, keep_images=False):
        super().__init__()
        self.parts = []
        self.skip = False
        self.keep_links = keep_links
        self.keep_images = keep_images
        self._links = []  # Stapel offener <a>: [href, [textteile]]

    def _emit(self, s):
        # In einen offenen <a> schreiben wir in dessen Textpuffer, damit der
        # Link am </a> als [text](href) ausgegeben werden kann.
        if self._links:
            self._links[-1][1].append(s)
        else:
            self.parts.append(s)

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip = True
            return
        a = dict(attrs)
        if tag == "a" and self.keep_links:
            self._links.append([a.get("href"), []])
        elif tag == "img" and self.keep_images:
            src = (a.get("src") or "").strip()
            # Tracking-Pixel (1x1) und inline-base64-Bilder rauslassen.
            if (src and not src.startswith("data:")
                    and a.get("width") not in ("0", "1")
                    and a.get("height") not in ("0", "1")):
                alt = (a.get("alt") or "").strip()
                self._emit(f" ![{alt}]({src}) ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = False
            return
        if tag == "a" and self.keep_links and self._links:
            href, textparts = self._links.pop()
            text = "".join(textparts).strip()
            if href and not href.startswith(("javascript:", "#")):
                self._emit(f"[{text}]({href})" if text else f"({href})")
            else:
                self._emit(text)

    def handle_data(self, data):
        if not self.skip:
            self._emit(data)


def html_to_text(html, keep_links=False, keep_images=False):
    if not html:
        return ""
    p = _Stripper(keep_links=keep_links, keep_images=keep_images)
    try:
        p.feed(html)
        # Offene <a> ohne </a> noch ausspielen, damit kein Link verschluckt wird.
        while p._links:
            href, textparts = p._links.pop()
            text = "".join(textparts).strip()
            if href and not href.startswith(("javascript:", "#")):
                p.parts.append(f"[{text}]({href})" if text else f"({href})")
            else:
                p.parts.append(text)
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
