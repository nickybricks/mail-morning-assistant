#!/usr/bin/env python3
"""Liest die E-Mails der letzten N Stunden aus dem Gmail-Postfach (INBOX + Spam)
ueber die Gmail-REST-API (HTTPS) und gibt sie als JSON auf stdout aus — gleiches
Schema wie adapters/imap/fetch_mail.py, damit core/briefing.md unveraendert
weiterverarbeiten kann. Veraendert das Postfach NICHT (nur Lesezugriffe).

Anders als der Gmail-MCP liefert format=raw die vollstaendige RFC822-MIME inkl.
Authentication-Results-Header -> DMARC/SPF/DKIM-Verdict ist hier verfuegbar.

Funktioniert im claude.ai-Cloud-Environment (nur 443/HTTPS), wo IMAP gesperrt ist.
"""
import base64
import email
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _gmail_common import load_config, access_token, api, die  # noqa: E402
from _mime import decode_header_value, extract_body, extract_auth  # noqa: E402

LOOKBACK_HOURS = 24


def list_ids(token, query):
    """Alle Message-IDs zu einer Gmail-Query (mit Pagination)."""
    ids, page = [], None
    while True:
        params = {"q": query, "maxResults": 500}
        if page:
            params["pageToken"] = page
        resp = api("GET", "/messages", token, params=params)
        ids.extend(m["id"] for m in resp.get("messages", []))
        page = resp.get("nextPageToken")
        if not page:
            return ids


def fetch_raw(token, msg_id):
    resp = api("GET", f"/messages/{msg_id}", token, params={"format": "raw"})
    raw = base64.urlsafe_b64decode(resp["raw"].encode())
    return email.message_from_bytes(raw), resp.get("threadId")


def last_briefing_epoch(token, name):
    """Zeitpunkt (epoch sec) des letzten ausgelieferten Briefings, oder None.
    Dient als Zeitmarke fuer mehrmals-taegliche Laeufe: jeder Lauf briefed nur,
    was seit dem letzten Briefing kam. Gmail selbst ist die Marke (kein State)."""
    resp = api("GET", "/messages", token,
               params={"q": f"label:{name}/Briefings", "maxResults": 1})
    msgs = resp.get("messages", [])
    if not msgs:
        return None
    m = api("GET", f"/messages/{msgs[0]['id']}", token, params={"format": "minimal"})
    try:
        return int(m["internalDate"]) / 1000.0
    except (KeyError, ValueError, TypeError):
        return None


def main():
    cfg = load_config()
    name = cfg.get("assistant_name") or "Maily"
    try:
        lookback = float(os.environ.get("MAIL_LOOKBACK_HOURS")
                         or cfg.get("lookback_hours") or LOOKBACK_HOURS)
    except (TypeError, ValueError):
        lookback = LOOKBACK_HOURS

    token = access_token(cfg["email"])

    now = datetime.now(timezone.utc)
    # Standard: seit dem letzten Briefing (fuer mehrmals-taegliche Laeufe -> keine
    # Wiederholung, kein Loch). Fallback: lookback_hours, wenn noch kein Briefing
    # existiert oder MAIL_LOOKBACK_HOURS das Fenster bewusst erzwingt.
    since = None
    if not os.environ.get("MAIL_LOOKBACK_HOURS"):
        last = last_briefing_epoch(token, name)
        if last is not None:
            # 10 min Puffer: Mail, die zeitgleich mit dem Briefing kam, nicht verlieren.
            since = datetime.fromtimestamp(last - 600, tz=timezone.utc)
    if since is None:
        since = now - timedelta(hours=lookback)

    # Gmail newer_than ist tagesgenau -> einen Tag weiter zuruecksuchen, danach
    # exakt nach Date-Header filtern (wie der IMAP-Adapter).
    window_h = max((now - since).total_seconds() / 3600.0, 1.0)
    days_wide = int(math.ceil(window_h / 24)) + 1

    # Eigene Briefings nie mit-briefen.
    sources = [
        (f"newer_than:{days_wide}d in:inbox -label:{name}/Briefings", "INBOX", False),
        (f"newer_than:{days_wide}d in:spam", "Spam", True),
    ]

    by_key = {}
    for query, folder, is_spam in sources:
        try:
            ids = list_ids(token, query)
        except SystemExit:
            raise
        except Exception as e:
            die(f"Gmail-Suche '{query}' fehlgeschlagen: {e}")
        for mid_g in ids:
            try:
                msg, thread_id = fetch_raw(token, mid_g)
            except SystemExit:
                raise
            except Exception:
                continue
            dt = None
            try:
                dt = parsedate_to_datetime(msg.get("Date"))
                if dt is not None and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                dt = None
            if dt is None or dt < since:
                continue
            mid = (msg.get("Message-ID") or "").strip()
            entry = {
                "uid": mid_g,                 # Gmail-Message-ID (fuer modify/Threading)
                "thread_id": thread_id,
                "folder": folder,
                "is_spam": is_spam,
                "message_id": mid,
                "in_reply_to": (msg.get("In-Reply-To") or "").strip(),
                "references": (msg.get("References") or "").strip(),
                "from": decode_header_value(msg.get("From")),
                "to": decode_header_value(msg.get("To")),
                "subject": decode_header_value(msg.get("Subject")),
                "date": dt.isoformat(),
                "auth": extract_auth(msg),
                "body": extract_body(msg),
            }
            key = mid or f"_nomid::{folder}::{mid_g}"
            existing = by_key.get(key)
            # Nicht-Spam schlaegt Spam (gleiche Mail kann doppelt auftauchen).
            if existing is None or (existing.get("is_spam") and not is_spam):
                by_key[key] = entry

    emails = sorted(by_key.values(), key=lambda x: x.get("date", ""), reverse=True)
    print(json.dumps({"count": len(emails), "emails": emails},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
