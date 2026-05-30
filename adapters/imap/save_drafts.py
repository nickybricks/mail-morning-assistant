#!/usr/bin/env python3
"""Legt Antwort-Entwuerfe im Drafts-Ordner ab (erscheinen automatisch in
Apple Mail) und markiert/verschiebt Mails nach Plan. Sendet NICHTS und
loescht NICHTS dauerhaft.

Aufruf:  python3 scripts/save_drafts.py <plan.json> [--dry-run]

plan.json:
{
  "drafts": [
    {"to": "...", "subject": "Re: ...", "body": "...",
     "in_reply_to": "<id>", "references": "<id> <id>"}
  ],
  "actions": [
    {"uid": "123", "folder": "INBOX", "flag": true},
    {"uid": "456", "folder": "INBOX", "move_to": "Newsletter"}
  ]
}

`folder` ist optional und faellt auf INBOX zurueck. Pflicht, sobald die Mail
in einem Unterordner liegt -- UIDs sind pro Ordner eindeutig, nicht global.
"""

import imaplib
import json
import re
import sys
import time
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _imap_common import (  # noqa: E402
    load_config, connect_imap, die, imap_utf7_encode,
)

DRAFTS_CANDIDATES = ("Drafts", "INBOX.Drafts", "Entwürfe", "INBOX.Entwürfe",
                     "INBOX.Drafts/Drafts")


def list_folders(conn):
    typ, data = conn.list()
    folders = []
    if typ == "OK":
        for line in data:
            if line is None:
                continue
            s = line.decode(errors="replace")
            flag_part = s.split(")")[0] if ")" in s else s
            flags = [f.lower() for f in re.findall(r"\\[A-Za-z]+", flag_part)]
            names = re.findall(r'"([^"]*)"', s)
            name = names[-1] if names else s.split()[-1]
            folders.append((name, flags))
    return folders


def find_drafts_folder(conn, cfg):
    if cfg.get("drafts_folder"):
        return cfg["drafts_folder"]
    folders = list_folders(conn)
    for name, flags in folders:
        if "\\drafts" in flags:
            return name
    existing = {name for name, _ in folders}
    for cand in DRAFTS_CANDIDATES:
        if cand in existing:
            return cand
    return "INBOX.Drafts"


def normalize_folder(name, drafts_folder):
    """Falls der Server eine INBOX.* Hierarchie nutzt (Dovecot/all-inkl),
    Zielordner entsprechend einordnen."""
    if drafts_folder.lower().startswith("inbox.") and "." in drafts_folder:
        if "." not in name and not name.lower().startswith("inbox."):
            return "INBOX." + name
    return name


def append_draft(conn, cfg, d, drafts_folder):
    em = EmailMessage()
    em["From"] = cfg["email"]
    em["To"] = d["to"]
    em["Subject"] = d.get("subject", "")
    em["Date"] = formatdate(localtime=True)
    em["Message-ID"] = make_msgid()
    if d.get("in_reply_to"):
        em["In-Reply-To"] = d["in_reply_to"]
    refs = " ".join(x for x in (d.get("references", ""), d.get("in_reply_to", "")) if x).strip()
    if refs:
        em["References"] = refs
    em.set_content(d.get("body", ""))
    conn.append(drafts_folder, "(\\Draft)",
                imaplib.Time2Internaldate(time.time()), em.as_bytes())


def do_action(conn, action, drafts_folder):
    # Ordnernamen aus dem Plan sind lesbar (dekodiert) -> fuer IMAP enkodieren.
    source = imap_utf7_encode(action.get("folder") or "INBOX")
    conn.select('"%s"' % source)
    uid = action["uid"]
    if isinstance(uid, str):
        uid = uid.encode()
    if action.get("flag"):
        conn.uid("store", uid, "+FLAGS", "(\\Flagged)")
    target = action.get("move_to")
    if target:
        target = imap_utf7_encode(normalize_folder(target, drafts_folder))
        try:
            conn.create(target)  # existiert evtl. schon -> egal
        except imaplib.IMAP4.error:
            pass
        typ, _ = conn.uid("move", uid, target)  # RFC 6851 (Dovecot kann das)
        if typ != "OK":
            conn.uid("copy", uid, target)
            conn.uid("store", uid, "+FLAGS", "(\\Deleted)")
            conn.expunge()


def main():
    if len(sys.argv) < 2:
        die("Aufruf: save_drafts.py <plan.json> [--dry-run]")
    dry = "--dry-run" in sys.argv
    with open(sys.argv[1], encoding="utf-8") as f:
        plan = json.load(f)

    cfg = load_config()
    conn = connect_imap(cfg)
    result = {"drafts_saved": 0, "flagged": 0, "moved": 0,
              "dry_run": dry, "errors": []}
    try:
        drafts_folder = find_drafts_folder(conn, cfg)
        result["drafts_folder"] = drafts_folder
        for d in plan.get("drafts", []):
            try:
                if not dry:
                    append_draft(conn, cfg, d, drafts_folder)
                result["drafts_saved"] += 1
            except Exception as e:
                result["errors"].append(f"Entwurf an {d.get('to')}: {e}")
        for a in plan.get("actions", []):
            try:
                if not dry:
                    do_action(conn, a, drafts_folder)
                if a.get("flag"):
                    result["flagged"] += 1
                if a.get("move_to"):
                    result["moved"] += 1
            except Exception as e:
                result["errors"].append(f"Aktion uid {a.get('uid')}: {e}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        try:
            conn.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
