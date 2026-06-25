#!/usr/bin/env python3
"""Liest die zuletzt zugestellten AI-Digests aus dem eigenen Postfach zurueck —
Grundlage fuers Entdoppeln ueber Tage hinweg (siehe core/briefing.md, Abschnitt
"AI-Digest"). Der taegliche Cloud-Lauf laeuft in einem frischen Repo-Klon ohne
lokales Gedaechtnis; das einzige, was den Tag ueberlebt, sind die alten Digests
selbst — abgelegt unter dem Label aus config.json ('ai_digest_label'). Dieses
Skript holt die letzten N davon und gibt ihren Text aus, damit der naechste Lauf
weiss, was er gestern schon gebracht hat. Veraendert das Postfach NICHT.

Funktioniert ueber HTTPS -> auch im claude.ai-Cloud-Environment (kein IMAP).

Aufruf:  python3 fetch_prev_digests.py
ENV/Config:
- ai_digest_label   (config.json): Label, unter dem die Digests liegen.
                    Default: "<assistant_name>/AI-Digest".
- MAIL_PREV_DIGESTS (ENV, Default 2): wie viele vergangene Digests zurueckgeben.
"""
import base64
import email
import json
import os
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _gmail_common import load_config, access_token, api, resolve_label  # noqa: E402
from _mime import decode_part, html_to_text  # noqa: E402

DEFAULT_COUNT = 2


def extract_text(msg):
    """Den lesbaren Text der Digest-Mail (bevorzugt HTML -> Text, sonst Plain)."""
    text, html = None, None
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            ctype = part.get_content_type()
            if ctype == "text/html" and html is None:
                html = decode_part(part)
            elif ctype == "text/plain" and text is None:
                text = decode_part(part)
    else:
        payload = decode_part(msg)
        if msg.get_content_type() == "text/html":
            html = payload
        else:
            text = payload
    if html:
        return html_to_text(html, keep_links=False, keep_images=False).strip()
    return (text or "").strip()


def main():
    cfg = load_config()
    name = cfg.get("assistant_name") or "Maily"
    label = cfg.get("ai_digest_label") or f"{name}/AI-Digest"
    try:
        count = int(os.environ.get("MAIL_PREV_DIGESTS") or DEFAULT_COUNT)
    except (TypeError, ValueError):
        count = DEFAULT_COUNT

    token = access_token(cfg["email"])

    label_id = resolve_label(token, label, create=False)
    if not label_id:
        # Label existiert noch nicht -> es gab noch keinen Digest. Kein Fehler.
        print(json.dumps({"count": 0, "label": label, "digests": []},
                         ensure_ascii=False, indent=2))
        return

    # maxResults etwas groesser als count: defekte/leere Mails ueberspringen koennen.
    resp = api("GET", "/messages", token,
               params={"labelIds": [label_id], "maxResults": count + 3})
    ids = [m["id"] for m in resp.get("messages", [])]

    digests = []
    for mid in ids:
        if len(digests) >= count:
            break
        try:
            r = api("GET", f"/messages/{mid}", token, params={"format": "raw"})
            msg = email.message_from_bytes(base64.urlsafe_b64decode(r["raw"].encode()))
        except Exception:
            continue
        try:
            dt = parsedate_to_datetime(msg.get("Date"))
            date = dt.isoformat() if dt else None
        except Exception:
            date = None
        text = extract_text(msg)
        if not text:
            continue
        digests.append({
            "subject": msg.get("Subject"),
            "date": date,
            "text": text,
        })

    print(json.dumps({"count": len(digests), "label": label, "digests": digests},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
