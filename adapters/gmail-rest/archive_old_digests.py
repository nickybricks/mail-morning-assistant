#!/usr/bin/env python3
"""Archiviert alte, ungelesene AI-Digests, indem das INBOX-Label entfernt wird.
Die Mails bleiben im Label <assistant_name>/AI-Digest erhalten; sie verschwinden
nur aus dem Posteingang. Nichts wird geloescht.

Aufruf nach dem Zustellen des neuen Digests:
  python3 archive_old_digests.py <unread_digests.json>

<unread_digests.json> ist die Ausgabe von:
  python3 fetch_prev_digests.py --unread-inbox > unread_digests.json

Verarbeitet alle Eintraege mit "message_id" darin. Mails ohne message_id werden
uebersprungen (safety: nie blind archivieren).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gmail_common import load_config, access_token, api  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Aufruf: archive_old_digests.py <unread_digests.json>"},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    digests = data.get("digests", [])
    ids_to_archive = [d["message_id"] for d in digests if d.get("message_id")]

    if not ids_to_archive:
        print(json.dumps({"archived": 0, "note": "Keine alten Digests zum Archivieren."},
                         ensure_ascii=False, indent=2))
        return

    cfg = load_config()
    token = access_token(cfg["email"])

    archived, errors = [], []
    for mid in ids_to_archive:
        try:
            api("POST", f"/messages/{mid}/modify", token,
                body={"removeLabelIds": ["INBOX"]})
            archived.append(mid)
        except Exception as e:
            errors.append({"message_id": mid, "error": str(e)})

    result = {
        "archived": len(archived),
        "archived_ids": archived,
        "note": "INBOX-Label entfernt; Mails bleiben im AI-Digest-Label.",
    }
    if errors:
        result["errors"] = errors
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
