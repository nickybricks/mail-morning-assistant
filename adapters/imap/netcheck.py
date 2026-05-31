#!/usr/bin/env python3
"""Diagnose: Welche ausgehenden Verbindungen erlaubt diese (Cloud-)Umgebung?

Klärt, ob ein Cloud-Lauf IMAP (Port 993) überhaupt erreichen kann, oder ob das
Environment nur HTTPS (443) nach außen lässt. Nichts Geheimes, nur Verbindungs-
Tests. Aufruf: python3 adapters/imap/netcheck.py
"""
import json
import socket

TIMEOUT = 8


def dns(host):
    try:
        addrs = sorted({i[4][0] for i in socket.getaddrinfo(host, None)})
        fams = sorted({i[0].name for i in socket.getaddrinfo(host, None)})
        return {"ok": True, "addrs": addrs, "families": fams}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def tcp(host, port):
    try:
        s = socket.create_connection((host, port), timeout=TIMEOUT)
        s.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


out = {
    "dns_imap_gmail": dns("imap.gmail.com"),
    "tcp_imap_gmail_993": tcp("imap.gmail.com", 993),
    "tcp_gmail_443": tcp("gmail.com", 443),
    "tcp_google_443": tcp("www.google.com", 443),
}
# Kurzfazit
egress_993 = out["tcp_imap_gmail_993"]["ok"]
egress_443 = out["tcp_gmail_443"]["ok"] or out["tcp_google_443"]["ok"]
if egress_993:
    out["fazit"] = "IMAP (993) erreichbar -> Cloud-IMAP funktioniert."
elif egress_443:
    out["fazit"] = "Nur HTTPS (443) erreichbar, IMAP (993) blockiert -> IMAP im Cloud-Env nicht möglich."
else:
    out["fazit"] = "Gar kein ausgehender Zugriff -> Cloud-Env kann nicht nach außen."
print(json.dumps(out, indent=2, ensure_ascii=False))
