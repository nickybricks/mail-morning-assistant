#!/usr/bin/env python3
"""Legt die Morgen-Briefing-Mail per Gmail messages.insert ins Postfach -- self-
addressed (von dir an dich), ungelesen, mit Label <assistant_name>/Briefings
(und INBOX). Kein Versand: messages.insert legt die Mail nur ab, sie geht nicht
an Dritte raus und durchlaeuft keinen Spam-Filter.

Funktioniert ueber HTTPS -> auch im claude.ai-Cloud-Environment (kein IMAP).

Aufruf:  python3 deliver_briefing.py <briefing.txt> [--folder "Maily/Briefings"]
                                     [--subject "..."] [--also-inbox] [--html]
                                     [--dry-run]

- <briefing.txt>: Briefing-Text (UTF-8), inkl. Kosten-Footer.
- --folder:   Ziel-Label. Default: "<assistant_name>/Briefings".
- --subject:  Betreff. Default: "<assistant_name>-Briefing — <Datum>".
- --also-inbox: zusaetzlich INBOX-Label (Briefing bleibt morgens sichtbar).
- --html:     Datei als HTML behandeln -> Mail als HTML zustellen (Links klickbar,
              Bilder inline). Gebraucht fuer den AI-Digest. Ohne Flag: reiner Text.
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

# Fester Rahmen fuer HTML-Mails (AI-Digest): nagelt Schriftart und -groesse fest,
# damit jeder Tag identisch aussieht. Ohne font-family rendern manche Clients
# (Apple Mail) unstyltes HTML als Times New Roman; ohne font-size wird es mal
# winzig. Der Inhalt vom Modell ist nur das innere Fragment (Abschnitte/Bullets);
# Typografie kommt hier deterministisch drumherum. Inline-style, weil Gmail
# <style>-Bloecke entfernt.
HTML_SHELL = (
    '<div style="max-width:680px;margin:0 auto;padding:16px 20px;'
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,"
    'Arial,sans-serif;font-size:16px;line-height:1.55;color:#1a1a1a;'
    'background:#ffffff;">{body}</div>'
)


def wrap_html(body):
    """Inhalts-Fragment in den festen Rahmen legen. Liefert das Modell ausnahmsweise
    schon ein komplettes Dokument (<html>/<body>), bleibt es unangetastet."""
    low = body.lower()
    if "<html" in low or "<body" in low:
        return body
    return HTML_SHELL.format(body=body)


def build_raw(cfg, subject, body, html=False):
    em = EmailMessage()
    addr = cfg["email"]
    em["From"] = addr
    em["To"] = addr
    em["Subject"] = subject
    em["Date"] = formatdate(localtime=True)
    em["Message-ID"] = make_msgid(domain=addr.split("@")[-1])
    if html:
        # multipart/alternative: knapper Text-Fallback + die HTML-Version (Links
        # klickbar, Bilder inline). Clients ohne HTML zeigen den Fallback.
        em.set_content("Dieser AI-Digest ist als HTML-Mail formatiert. "
                       "Bitte in einem Client mit HTML-Ansicht oeffnen.")
        em.add_alternative(wrap_html(body), subtype="html")
    else:
        em.set_content(body)
    return base64.urlsafe_b64encode(em.as_bytes()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("briefing")
    ap.add_argument("--folder")
    ap.add_argument("--subject")
    ap.add_argument("--also-inbox", action="store_true")
    ap.add_argument("--html", action="store_true")
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
        raw = build_raw(cfg, subject, body, html=args.html)
        inserted = api("POST", "/messages", token,
                       params={"internalDateSource": "dateHeader"},
                       body={"raw": raw, "labelIds": label_ids})
        result["message_id"] = inserted.get("id")
        result["thread_id"] = inserted.get("threadId")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
