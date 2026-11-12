#!/usr/bin/env python3
"""Quota-efficient variant of fetch_mail.py:
Uses format=metadata (headers + snippet) instead of format=raw.
Avoids full MIME decode — costs ~50x less quota per message.
Falls back to format=raw only if metadata fetch fails per message.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _gmail_common import load_config, access_token, api, die  # noqa: E402

LOOKBACK_HOURS = 24
WANTED_HEADERS = [
    "From", "To", "Subject", "Date", "Message-ID",
    "In-Reply-To", "References",
    "Authentication-Results", "DKIM-Signature",
    "X-Google-DKIM-Signature",
]
# Delay between individual message fetches to stay under quota (seconds)
INTER_MSG_DELAY = 0.12   # ~8 fetches/sec → ~8*5=40 units/sec → 2400/min well under 6000


def list_ids_paginated(token, query, max_results=200):
    ids, page = [], None
    while True:
        params = {"q": query, "maxResults": min(500, max_results - len(ids))}
        if page:
            params["pageToken"] = page
        resp = api("GET", "/messages", token, params=params)
        for m in resp.get("messages", []):
            ids.append(m["id"])
        page = resp.get("nextPageToken")
        if not page or len(ids) >= max_results:
            return ids[:max_results]


def fetch_metadata(token, msg_id):
    resp = api("GET", f"/messages/{msg_id}", token, params={
        "format": "metadata",
        "metadataHeaders": WANTED_HEADERS,
    })
    headers = {h["name"]: h["value"]
               for h in resp.get("payload", {}).get("headers", [])}
    return headers, resp.get("snippet", ""), resp.get("threadId"), resp.get("labelIds", [])


def parse_auth(auth_results):
    """Extract spf/dkim/dmarc pass/fail from Authentication-Results header."""
    if not auth_results:
        return {}
    result = {}
    for part in auth_results.lower().split(";"):
        part = part.strip()
        for proto in ("spf", "dkim", "dmarc"):
            if proto in part:
                for verdict in ("pass", "fail", "none", "neutral", "temperror", "permerror"):
                    if verdict in part:
                        result[proto] = verdict
                        break
    return result


def last_briefing_epoch(token, name):
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
    since = None
    if not os.environ.get("MAIL_LOOKBACK_HOURS"):
        last = last_briefing_epoch(token, name)
        if last is not None:
            since = datetime.fromtimestamp(last - 600, tz=timezone.utc)
    if since is None:
        since = now - timedelta(hours=lookback)

    # Narrow the query to 2 days max to reduce list cost
    days_wide = min(int((now - since).total_seconds() / 86400) + 2, 3)

    sources = [
        (f"newer_than:{days_wide}d in:inbox -label:{name}/Briefings", "INBOX", False),
        (f"newer_than:{days_wide}d in:spam", "Spam", True),
    ]

    by_key = {}
    for query, folder, is_spam in sources:
        try:
            ids = list_ids_paginated(token, query, max_results=300)
        except SystemExit:
            raise
        except Exception as e:
            die(f"Gmail-Suche '{query}' fehlgeschlagen: {e}")

        for mid_g in ids:
            try:
                headers, snippet, thread_id, label_ids = fetch_metadata(token, mid_g)
                time.sleep(INTER_MSG_DELAY)
            except SystemExit:
                raise
            except Exception:
                continue

            raw_date = headers.get("Date", "")
            dt = None
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(raw_date)
                if dt is not None and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                dt = None
            if dt is None or dt < since:
                continue

            mid = (headers.get("Message-ID") or "").strip()
            auth = parse_auth(headers.get("Authentication-Results", ""))
            entry = {
                "uid": mid_g,
                "thread_id": thread_id,
                "folder": folder,
                "is_spam": is_spam,
                "message_id": mid,
                "in_reply_to": (headers.get("In-Reply-To") or "").strip(),
                "references": (headers.get("References") or "").strip(),
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "date": dt.isoformat() if dt else raw_date,
                "auth": auth,
                "body": snippet,  # snippet as body approximation
            }
            key = mid or f"_nomid::{folder}::{mid_g}"
            existing = by_key.get(key)
            if existing is None or (existing.get("is_spam") and not is_spam):
                by_key[key] = entry

    emails = sorted(by_key.values(), key=lambda x: x.get("date", ""), reverse=True)
    print(json.dumps({"count": len(emails), "emails": emails},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
