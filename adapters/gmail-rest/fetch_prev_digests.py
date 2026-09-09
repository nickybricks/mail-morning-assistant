#!/usr/bin/env python3
"""Liest die zuletzt zugestellten AI-Digests aus dem eigenen Postfach zurueck —
Grundlage fuers Entdoppeln ueber Tage hinweg (siehe core/briefing.md, Abschnitt
"AI-Digest"). Der taegliche Cloud-Lauf laeuft in einem frischen Repo-Klon ohne
lokales Gedaechtnis; das einzige, was den Tag ueberlebt, sind die alten Digests
selbst — abgelegt unter dem Label aus config.json ('ai_digest_label'). Dieses
Skript holt die letzten N davon und gibt ihren Text aus, damit der naechste Lauf
weiss, was er gestern schon gebracht hat. Veraendert das Postfach NICHT.

Funktioniert ueber HTTPS -> auch im claude.ai-Cloud-Environment (kein IMAP).

Aufruf:  python3 fetch_prev_digests.py [--unread-inbox]
Flags:
- --unread-inbox: Nur noch ungelesene Digests zurueckgeben, die sich noch in der
  INBOX befinden. Liefert ausserdem die message_id jedes Digests (Eingabe fuer
  archive_old_digests.py). Ohne dieses Flag: wie bisher, alle letzten N Digests.
ENV/Config:
- ai_digest_label   (config.json): Label, unter dem die Digests liegen.
                    Default: "<assistant_name>/AI-Digest".
- MAIL_PREV_DIGESTS (ENV, Default 2): wie viele vergangene Digests zurueckgeben.
"""
import argparse
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--unread-inbox", action="store_true",
                    help="Nur noch ungelesene Digests in der INBOX zurueckgeben "
                         "(mit message_id, Eingabe fuer archive_old_digests.py).")
    args = ap.parse_args()

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

    # Bei --unread-inbox: nur Mails, die INBOX + UNREAD + Digest-Label haben.
    # Ohne Flag: alle letzten N Digests (wie bisher).
    if args.unread_inbox:
        label_ids_filter = [label_id, "INBOX", "UNREAD"]
        max_results = 10  # realistisches Maximum ungelesener Digests
    else:
        label_ids_filter = [label_id]
        max_results = count + 3  # etwas groesser: defekte Mails ueberspringen

    resp = api("GET", "/messages", token,
               params={"labelIds": label_ids_filter, "maxResults": max_results})
    ids = [m["id"] for m in resp.get("messages", [])]

    digests = []
    for mid in ids:
        if not args.unread_inbox and len(digests) >= count:
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
        entry = {
            "subject": msg.get("Subject"),
            "date": date,
            "text": text,
        }
        if args.unread_inbox:
            entry["message_id"] = mid
        digests.append(entry)

    # Bei --unread-inbox: aelteste zuerst (chronologisch aufsteigend), damit der
    # Inhalt in der richtigen Zeitreihenfolge ins neue Digest eingebaut werden kann.
    if args.unread_inbox:
        digests.sort(key=lambda d: d.get("date") or "")

    print(json.dumps({"count": len(digests), "label": label, "digests": digests},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
