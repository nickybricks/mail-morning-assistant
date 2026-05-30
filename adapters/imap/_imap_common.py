"""Gemeinsame Helfer fuer den IMAP-Adapter: Konfiguration laden, Passwort holen,
IMAP verbinden.

Das Passwort wird NIE in einer Datei gespeichert. Es kommt aus dem macOS-
Schluesselbund (empfohlen) oder aus der Umgebungsvariable MAIL_IMAP_PASSWORD.

config.json liegt im Skill-Wurzelverzeichnis (zwei Ebenen ueber dieser Datei).
"""

import base64
import imaplib
import json
import os
import ssl
import subprocess
import sys
from pathlib import Path


# --- IMAP "modified UTF-7" (RFC 3501 5.1.3) ------------------------------
# Ordnernamen kommen vom Server in dieser Kodierung (z. B. Emojis/Umlaute:
# "Privat/Amazon &2D3c5g-"). Fuer Anzeige/JSON dekodieren, fuer IMAP-Befehle
# (SELECT/MOVE/CREATE) wieder enkodieren.

def imap_utf7_decode(name):
    res, i, n = [], 0, len(name)
    while i < n:
        c = name[i]
        if c == "&":
            j = name.find("-", i)
            if j == -1:           # defekt -> Rest literal
                res.append(name[i:]); break
            chunk = name[i + 1:j]
            if chunk == "":
                res.append("&")   # "&-" steht fuer ein literales "&"
            else:
                b64 = chunk.replace(",", "/")
                pad = "=" * (-len(b64) % 4)
                res.append(base64.b64decode(b64 + pad).decode("utf-16-be"))
            i = j + 1
        else:
            res.append(c); i += 1
    return "".join(res)


def imap_utf7_encode(name):
    res, i, n = [], 0, len(name)
    while i < n:
        o = ord(name[i])
        if 0x20 <= o <= 0x7e:
            res.append("&-" if name[i] == "&" else name[i])
            i += 1
        else:
            j = i
            while j < n and not (0x20 <= ord(name[j]) <= 0x7e):
                j += 1
            b64 = base64.b64encode(name[i:j].encode("utf-16-be")).decode("ascii")
            res.append("&" + b64.rstrip("=").replace("/", ",") + "-")
            i = j
    return "".join(res)

# adapters/imap/_imap_common.py -> Skill-Wurzel = parents[2]
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.json"

DEFAULT_KEYCHAIN_SERVICE = "mail-imap"


def die(msg):
    """Fehler als JSON auf stderr ausgeben und beenden (der Assistent liest das)."""
    print(json.dumps({"error": msg}, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


def load_config():
    if not CONFIG_PATH.exists():
        die(f"config.json fehlt unter {CONFIG_PATH}. "
            "Bitte config.example.json kopieren und ausfuellen "
            "(oder das Onboarding starten).")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    if cfg.get("provider") and cfg.get("provider") != "imap":
        die(f"config.json: provider ist '{cfg.get('provider')}', "
            "dieser Adapter ist nur fuer 'imap'.")
    for key in ("imap_host", "email"):
        if not cfg.get(key):
            die(f"config.json: Pflichtfeld '{key}' fehlt oder ist leer.")
    cfg.setdefault("imap_port", 993)
    cfg.setdefault("keychain_service", DEFAULT_KEYCHAIN_SERVICE)
    return cfg


def get_password(cfg):
    # 1) Umgebungsvariable (Fallback / fuer Tests)
    pw = os.environ.get("MAIL_IMAP_PASSWORD")
    if pw:
        return pw
    # 2) macOS-Schluesselbund (empfohlen)
    service = cfg.get("keychain_service", DEFAULT_KEYCHAIN_SERVICE)
    account = cfg["email"]
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True, text=True,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except FileNotFoundError:
        pass  # 'security' nur auf macOS vorhanden
    die("Kein Postfach-Passwort gefunden. Lege es im Schluesselbund ab "
        "(siehe adapters/imap/adapter.md) oder setze MAIL_IMAP_PASSWORD.")


def connect_imap(cfg):
    pw = get_password(cfg)
    ctx = ssl.create_default_context()
    try:
        conn = imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"], ssl_context=ctx)
        conn.login(cfg["email"], pw)
    except imaplib.IMAP4.error as e:
        die(f"IMAP-Login fehlgeschlagen: {e}. Host/E-Mail/Passwort pruefen. "
            "Viele Anbieter verlangen ein App-Passwort statt des normalen.")
    except OSError as e:
        die(f"Verbindung zu {cfg['imap_host']}:{cfg['imap_port']} fehlgeschlagen: {e}")
    return conn
