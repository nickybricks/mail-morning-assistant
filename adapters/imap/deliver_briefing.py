#!/usr/bin/env python3
"""Legt die Morgen-Briefing-Mail per IMAP APPEND in einen Ordner -- self-
addressed (von dir an dich), als ungelesene Nachricht. Kein SMTP-Versand,
nichts wird gesendet; die Mail wird nur lokal im Postfach abgelegt.

Aufruf:  python3 deliver_briefing.py <briefing.txt> [--folder "Maily/Briefings"]
                                     [--subject "..."] [--also-inbox] [--dry-run]

- <briefing.txt>: Briefing-Text (UTF-8), inkl. Kosten-Footer.
- --folder:   Zielordner. Default: "<assistant_name>/Briefings".
- --subject:  Betreff. Default: "<assistant_name>-Briefing — <Datum>".
- --also-inbox: zusaetzlich eine Kopie in INBOX (damit es morgens sichtbar ist).
- --dry-run:  nichts ablegen, nur zeigen, was passieren wuerde.
"""

import argparse
import imaplib
import sys
import time
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _imap_common import (  # noqa: E402
    load_config, connect_imap, die, imap_utf7_encode,
)


def build_message(cfg, subject, body):
    em = EmailMessage()
    addr = cfg["email"]
    em["From"] = addr
    em["To"] = addr
    em["Subject"] = subject
    em["Date"] = formatdate(localtime=True)
    em["Message-ID"] = make_msgid(domain=addr.split("@")[-1])
    em.set_content(body)
    return em


def append_to(conn, folder, em, dry):
    enc = imap_utf7_encode(folder)
    if dry:
        return f"(dry-run) wuerde anlegen in: {folder}"
    try:
        conn.create(enc)  # existiert evtl. schon -> egal
    except imaplib.IMAP4.error:
        pass
    # Keine Flags -> Mail erscheint als ungelesen.
    typ, data = conn.append(enc, None, imaplib.Time2Internaldate(time.time()),
                            em.as_bytes())
    if typ != "OK":
        raise RuntimeError(f"APPEND fehlgeschlagen fuer {folder}: {data}")
    return f"abgelegt in: {folder}"


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
    em = build_message(cfg, subject, body)

    conn = connect_imap(cfg)
    result = {"dry_run": args.dry_run, "subject": subject, "placed": []}
    try:
        result["placed"].append(append_to(conn, folder, em, args.dry_run))
        if args.also_inbox:
            result["placed"].append(append_to(conn, "INBOX", em, args.dry_run))
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
