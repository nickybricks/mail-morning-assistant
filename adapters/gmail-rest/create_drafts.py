#!/usr/bin/env python3
"""Legt Antwort-Entwürfe als Gmail-Drafts an (users.drafts.create) — über HTTPS,
cloud-tauglich. Es wird NIE gesendet: drafts.create erzeugt ausschließlich einen
Entwurf im Drafts-Ordner. Der Nutzer prüft und sendet selbst.

Eingabe: JSON mit den vom Modell formulierten Antworten (im Stil des Nutzers):

    {"drafts": [
        {"id": "<gmail-message-id der Originalmail>", "body": "<Antworttext inkl. Gruß/Signatur>"}
    ]}

Das Skript kümmert sich um das Threading (Modell liefert nur den Text):
- To       = Reply-To der Originalmail, sonst deren From (Antwort an den Absender).
- Subject  = "Re: <Originalbetreff>" (kein doppeltes "Re:").
- In-Reply-To / References = für saubere Thread-Einordnung.
- threadId = Thread der Originalmail (Draft erscheint im selben Verlauf).

Antwortet nur an den Absender (kein Reply-All) — CC fügt der Nutzer bei Bedarf hinzu.

    python3 create_drafts.py <drafts.json> [--dry-run]
"""
import argparse
import base64
import json
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gmail_common import load_config, access_token, api, die  # noqa: E402


def header_map(msg_meta):
    return {h["name"].lower(): h["value"] for h in msg_meta.get("payload", {}).get("headers", [])}


def existing_draft_threads(token):
    """Thread-IDs, in denen schon ein Entwurf liegt. Gmail selbst ist das
    'Gedaechtnis': so legt ein erneuter Lauf fuer denselben Thread keinen
    zweiten Entwurf an (idempotent, ohne State-Datei)."""
    threads, page = set(), None
    while True:
        params = {"maxResults": 500}
        if page:
            params["pageToken"] = page
        resp = api("GET", "/drafts", token, params=params)
        for d in resp.get("drafts", []):
            tid = (d.get("message") or {}).get("threadId")
            if tid:
                threads.add(tid)
        page = resp.get("nextPageToken")
        if not page:
            return threads


def build_reply_raw(cfg, orig_headers, body):
    addr = cfg["email"]
    to = orig_headers.get("reply-to") or orig_headers.get("from") or ""
    subj = orig_headers.get("subject", "")
    if not subj.lower().startswith("re:"):
        subj = "Re: " + subj
    orig_mid = orig_headers.get("message-id", "")
    refs = orig_headers.get("references", "")
    references = (refs + " " + orig_mid).strip() if refs else orig_mid

    em = EmailMessage()
    em["From"] = addr
    em["To"] = to
    em["Subject"] = subj
    em["Date"] = formatdate(localtime=True)
    em["Message-ID"] = make_msgid(domain=addr.split("@")[-1])
    if orig_mid:
        em["In-Reply-To"] = orig_mid
        em["References"] = references
    em.set_content(body)
    return base64.urlsafe_b64encode(em.as_bytes()).decode(), to, subj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("drafts")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    data = json.loads(Path(args.drafts).read_text(encoding="utf-8"))
    drafts = data.get("drafts", data) if isinstance(data, dict) else data
    if not isinstance(drafts, list):
        die("drafts-Datei: erwarte {\"drafts\": [...]} oder eine Liste.")

    token = access_token(cfg["email"])
    seen_threads = existing_draft_threads(token)
    result = {"dry_run": args.dry_run, "created": 0, "drafts": [], "skipped": [], "errors": []}

    for d in drafts:
        mid = d.get("id")
        body = d.get("body")
        if not mid or not body:
            result["errors"].append({"id": mid, "error": "id oder body fehlt"})
            continue
        try:
            meta = api("GET", f"/messages/{mid}", token,
                       params={"format": "metadata",
                               "metadataHeaders": ["From", "Reply-To", "Subject", "Message-ID", "References"]})
        except SystemExit as e:
            result["errors"].append({"id": mid, "error": str(e)})
            continue
        thread_id = meta.get("threadId")
        # Idempotenz: liegt im Thread schon ein Entwurf -> nicht erneut anlegen.
        if thread_id in seen_threads:
            result["skipped"].append({"id": mid, "thread_id": thread_id,
                                      "reason": "Entwurf existiert bereits in diesem Thread"})
            continue
        raw, to, subj = build_reply_raw(cfg, header_map(meta), body)

        seen_threads.add(thread_id)  # auch innerhalb dieses Laufs nicht doppeln
        if args.dry_run:
            result["created"] += 1
            result["drafts"].append({"reply_to_msg": mid, "to": to, "subject": subj,
                                     "thread_id": thread_id, "note": "(dry-run)"})
            continue
        try:
            created = api("POST", "/drafts", token,
                          body={"message": {"raw": raw, "threadId": thread_id}})
            result["created"] += 1
            result["drafts"].append({"reply_to_msg": mid, "to": to, "subject": subj,
                                     "draft_id": created.get("id")})
        except SystemExit as e:
            result["errors"].append({"id": mid, "error": str(e)})

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
