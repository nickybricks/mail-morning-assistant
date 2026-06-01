"""Gemeinsame OAuth-/HTTP-Helfer für den Gmail-REST-Adapter. Stdlib only.

Spricht die Gmail-REST-API über HTTPS (443) — der Weg, der auch im claude.ai-
Cloud-Environment funktioniert (IMAP/993 ist dort gesperrt, siehe
adapters/imap/netcheck.py).

Credentials-Quelle, in dieser Reihenfolge:
1. ENV  GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN  → Cloud-Lauf.
2. macOS-Schlüsselbund  Service `maily-gmail-rest` (oder ENV GMAIL_KEYCHAIN_SERVICE),
   Account = übergebene E-Mail  → lokaler Lauf. Wert ist ein JSON-Blob
   {client_id, client_secret, refresh_token}, wie oauth_bootstrap.py es ablegt.
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

TOKEN_URI = "https://oauth2.googleapis.com/token"
API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
DEFAULT_KEYCHAIN_SERVICE = "maily-gmail-rest"
# adapters/gmail-rest/_gmail_common.py -> Skill-Wurzel = parents[2]
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"


def die(msg):
    """Fehler als JSON auf stderr ausgeben und beenden (der Assistent liest das)."""
    print(json.dumps({"error": msg}, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


def load_config():
    if not CONFIG_PATH.exists():
        die(f"config.json fehlt unter {CONFIG_PATH}. config.example.json kopieren "
            "und ausfuellen (oder das Onboarding starten).")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    if cfg.get("provider") not in ("gmail-rest", "gmail"):
        die(f"config.json: provider ist '{cfg.get('provider')}', "
            "dieser Adapter ist fuer 'gmail-rest'.")
    if not cfg.get("email"):
        die("config.json: Pflichtfeld 'email' fehlt oder ist leer.")
    cfg.setdefault("lookback_hours", 24)
    cfg.setdefault("assistant_name", "Maily")
    return cfg


def _from_keychain(account: str):
    service = os.environ.get("GMAIL_KEYCHAIN_SERVICE", DEFAULT_KEYCHAIN_SERVICE)
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return None
    try:
        blob = json.loads(out)
    except json.JSONDecodeError:
        return None
    return blob.get("client_id"), blob.get("client_secret"), blob.get("refresh_token")


def load_credentials(account: str | None = None):
    """(client_id, client_secret, refresh_token) — ENV vor Schlüsselbund."""
    env = (os.environ.get("GMAIL_CLIENT_ID"),
           os.environ.get("GMAIL_CLIENT_SECRET"),
           os.environ.get("GMAIL_REFRESH_TOKEN"))
    if all(env):
        return env
    if account:
        kc = _from_keychain(account)
        if kc and all(kc):
            return kc
    raise SystemExit(
        "Keine Gmail-Credentials gefunden. Entweder ENV GMAIL_CLIENT_ID/"
        "GMAIL_CLIENT_SECRET/GMAIL_REFRESH_TOKEN setzen (Cloud) oder lokal erst "
        "oauth_bootstrap.py laufen lassen (Schlüsselbund)."
    )


def access_token(account: str | None = None) -> str:
    client_id, client_secret, refresh_token = load_credentials(account)
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URI, data=body, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def api(method: str, path: str, token: str, params: dict | None = None,
        body: dict | None = None, raw_body: bytes | None = None,
        content_type: str = "application/json"):
    """Ein Gmail-API-Call gegen .../users/me<path>. Retry bei 429/5xx."""
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = raw_body if raw_body is not None else (json.dumps(body).encode() if body is not None else None)
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = content_type

    last_err = None
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                payload = resp.read()
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                last_err = e
                time.sleep(2 ** attempt)
                continue
            detail = e.read().decode(errors="replace")
            raise SystemExit(f"Gmail API {method} {path} → HTTP {e.code}: {detail}")
    raise SystemExit(f"Gmail API {method} {path} → wiederholt fehlgeschlagen: {last_err}")


def resolve_label(token: str, name: str, create: bool = False) -> str | None:
    """Label-Name -> Gmail-Label-ID. System-Labels (INBOX/UNREAD/...) sind ihr
    eigener Name. Bei create=True wird ein fehlendes Label angelegt."""
    if name == name.upper() and "/" not in name:  # INBOX, UNREAD, SPAM, STARRED …
        return name
    labels = api("GET", "/labels", token).get("labels", [])
    for lab in labels:
        if lab["name"] == name:
            return lab["id"]
    if not create:
        return None
    created = api("POST", "/labels", token, body={
        "name": name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    })
    return created["id"]
