#!/usr/bin/env python3
"""Einmaliger lokaler OAuth-Bootstrap für den Gmail-REST-Adapter.

Holt per Loopback-Flow (PKCE) einen Refresh-Token für Scope gmail.modify und
legt {client_id, client_secret, refresh_token} als JSON im macOS-Schlüsselbund
ab (Service `maily-gmail-rest`). Anschließend ein Verify-Call gegen
users.getProfile. Stdlib only — keine pip-Pakete.

    python3 oauth_bootstrap.py /pfad/zu/client_secret_*.json

Den so gewonnenen Refresh-Token (+ client_id/secret) brauchst du danach als
Secrets im Cloud-Environment: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET,
GMAIL_REFRESH_TOKEN (das Skript gibt sie am Ende aus).
"""
import base64
import hashlib
import http.server
import json
import os
import secrets
import socket
import subprocess
import sys
import urllib.parse
import urllib.request
import webbrowser

SCOPE = "https://www.googleapis.com/auth/gmail.modify"
AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
PROFILE_URI = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
KEYCHAIN_SERVICE = "maily-gmail-rest"
KEYCHAIN_ACCOUNT = "nick@algner.de"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def load_client(path: str):
    with open(path) as fh:
        data = json.load(fh)
    node = data.get("installed") or data.get("web")
    if not node:
        sys.exit("client JSON: weder 'installed' noch 'web' Key — ist das ein OAuth-Client-Download?")
    return node["client_id"], node["client_secret"]


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _CodeHandler(http.server.BaseHTTPRequestHandler):
    code = None
    error = None

    def do_GET(self):
        qs = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(qs)
        _CodeHandler.code = params.get("code", [None])[0]
        _CodeHandler.error = params.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        msg = "Fehler: " + _CodeHandler.error if _CodeHandler.error else "Maily ist verbunden. Du kannst dieses Fenster schließen."
        self.wfile.write(f"<html><body style='font-family:sans-serif'><h2>{msg}</h2></body></html>".encode())

    def log_message(self, *args):  # noqa: A002 - silence default logging
        pass


def token_request(payload: dict) -> dict:
    body = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(TOKEN_URI, data=body, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_profile(access_token: str) -> dict:
    req = urllib.request.Request(PROFILE_URI, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def store_keychain(blob: dict):
    payload = json.dumps(blob)
    subprocess.run(
        ["security", "add-generic-password", "-s", KEYCHAIN_SERVICE,
         "-a", KEYCHAIN_ACCOUNT, "-w", payload, "-U"],
        check=True,
    )


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    client_id, client_secret = load_client(sys.argv[1])

    verifier = _b64url(secrets.token_bytes(40))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    port = free_port()
    redirect_uri = f"http://127.0.0.1:{port}/"

    auth_url = AUTH_URI + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })

    print("Öffne Browser zur Google-Anmeldung …")
    print("Falls nichts aufgeht, öffne diese URL manuell:\n" + auth_url + "\n")
    webbrowser.open(auth_url)

    server = http.server.HTTPServer(("127.0.0.1", port), _CodeHandler)
    server.handle_request()  # blockiert bis ein Request kommt
    server.server_close()

    if _CodeHandler.error:
        sys.exit("OAuth abgelehnt/abgebrochen: " + _CodeHandler.error)
    if not _CodeHandler.code:
        sys.exit("Kein Authorization-Code empfangen.")

    tokens = token_request({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": _CodeHandler.code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    })

    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")
    if not refresh_token:
        sys.exit("Kein refresh_token erhalten (prompt=consent + access_type=offline gesetzt?). Antwort: " + json.dumps(tokens))

    profile = get_profile(access_token)

    store_keychain({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    })

    print("\nOK — verbunden mit:", profile.get("emailAddress"))
    print("Postfach-Größe (messagesTotal):", profile.get("messagesTotal"))
    print(f"Refresh-Token im Schlüsselbund gespeichert (Service {KEYCHAIN_SERVICE}, Account {KEYCHAIN_ACCOUNT}).")
    print("\n=== Secrets fürs Cloud-Environment (claude.ai) ===")
    print("GMAIL_CLIENT_ID=" + client_id)
    print("GMAIL_CLIENT_SECRET=" + client_secret)
    print("GMAIL_REFRESH_TOKEN=" + refresh_token)


if __name__ == "__main__":
    main()
