#!/usr/bin/env python3
"""Legt die Morgen-Briefing-Mail per Gmail messages.insert ins Postfach -- self-
addressed (von dir an dich), ungelesen, mit Label <assistant_name>/Briefings
(und INBOX). Kein Versand: messages.insert legt die Mail nur ab, sie geht nicht
an Dritte raus und durchlaeuft keinen Spam-Filter.

Funktioniert ueber HTTPS -> auch im claude.ai-Cloud-Environment (kein IMAP).

Aufruf:  python3 deliver_briefing.py <briefing.txt> [--folder "Maily/Briefings"]
                                     [--subject "..."] [--also-inbox] [--dry-run]

- <briefing.txt>: Briefing-Text (UTF-8), inkl. Kosten-Footer.
- --folder:   Ziel-Label. Default: "<assistant_name>/Briefings".
- --subject:  Betreff. Default: "<assistant_name>-Briefing — <Datum>".
- --also-inbox: zusaetzlich INBOX-Label (Briefing bleibt morgens sichtbar).
- --dry-run:  nichts ablegen, nur zeigen, was passieren wuerde.
"""
import argparse
import base64
import json
import sys
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gmail_common import load_config, access_token, api, resolve_label  # noqa: E402


def build_raw(cfg, subject, body):
    em = EmailMessage()
    addr = cfg["email"]
    em["From"] = addr
    em["To"] = addr
    em["Subject"] = subject
    em["Date"] = formatdate(localtime=True)
    em["Message-ID"] = make_msgid(domain=addr.split("@")[-1])
    em.set_content(body)
    return base64.urlsafe_b64encode(em.as_bytes()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("briefing")
    ap.add_argument("--folder")
    ap.add_argument("--subject")
    ap.add_argument("--also-inbox", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    name = cfg.get("assistant_name") or "Mail"
    folder = args.folder or f"{name}/Briefings"
    subject = args.subject or f"{name}-Briefing — {datetime.now():%d.%m.%Y}"

    body = Path(args.briefing).read_text(encoding="utf-8")
    token = access_token(cfg["email"])

    label_id = resolve_label(token, folder, create=True)
    label_ids = [label_id, "UNREAD"]
    if args.also_inbox:
        label_ids.append("INBOX")

    result = {"dry_run": args.dry_run, "subject": subject,
              "folder": folder, "label_ids": label_ids}
    if args.dry_run:
        result["note"] = "(dry-run) wuerde messages.insert mit diesen Labels ausfuehren"
    else:
        raw = build_raw(cfg, subject, body)
        inserted = api("POST", "/messages", token,
                       params={"internalDateSource": "dateHeader"},
                       body={"raw": raw, "labelIds": label_ids})
        result["message_id"] = inserted.get("id")
        result["thread_id"] = inserted.get("threadId")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
