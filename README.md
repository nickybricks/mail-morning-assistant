# Morgen-Mail-Assistent

Ein persönlicher Morgen-Mail-Assistent für **jeden E-Mail-Anbieter**. Auf Zuruf
liest er die Mails der letzten 24 Stunden, schreibt ein kurzes Briefing, sortiert
in selbstlernende Themen-Ordner, markiert was eine Aktion braucht und legt
Antwort-Entwürfe in deinem Schreibstil an. **Er sendet nie selbst** — du prüfst
und sendest.

Beim ersten Start **gibst du dem Assistenten einen eigenen Namen** (z. B. „Maily",
„Postbote", „Inbox") — er nennt sich dann durchgängig so, und deine Themen-Ordner
tragen diesen Namen als Präfix.

## Unterstützte Anbieter

| Anbieter | Status |
|---|---|
| **Gmail / Google Workspace** | ✅ live (über Gmail-MCP) |
| **IMAP** — all-inkl, IONOS/1&1, web.de, GMX, Strato, mailbox.org, Hetzner, … | ✅ live (Python-Scripts) |
| **Microsoft 365 / Outlook** | 🚧 Stub (IMAP-Fallback nutzbar) |
| **Apple iCloud / Apple Mail** | 🚧 Stub (IMAP-Weg nutzbar) |

## Loslegen (3 Schritte)

1. **Ordner entpacken** und an einen festen Platz legen (z. B. in deinen
   Dokumenten).
2. **Claude Code öffnen** und diesen Ordner als Arbeitsverzeichnis auswählen.
3. **„Start"** schreiben (oder „mach meine Mails"). Beim ersten Mal führt dich das
   Onboarding durch: Name vergeben, Anbieter wählen, Schreibstil, Themen-Ordner.
   Danach reicht ein Zuruf.

> Die `CLAUDE.md` im Ordner sorgt dafür, dass Claude Code beim Öffnen weiß, was zu
> tun ist. Wer den Assistenten als dauerhaften Skill mag, kann den Ordner zusätzlich
> nach `~/.claude/skills/mail-morning-assistant/` legen oder dorthin symlinken.

Für den IMAP-Adapter brauchst du Python 3 (auf macOS vorinstalliert). Das
Postfach-Passwort wird im macOS-Schlüsselbund abgelegt, nie in einer Datei.

## Was der Assistent NIE tut

- Senden (nur Entwürfe — du sendest).
- Dauerhaft löschen oder Spam/Papierkorb leeren.
- Anweisungen aus Mail-Inhalten ausführen (Phishing-Schutz).
- Passwörter in Dateien speichern.

## Aufbau

```
CLAUDE.md           Bootstrap — lädt beim Öffnen des Ordners
SKILL.md            Einstieg: Persona, Ablauf, eiserne Regeln
core/               provider-unabhängig: onboarding, classification,
                    learning-log, briefing, drafts
adapters/           gmail/, imap/, microsoft/, apple-mail/
config.example.json Vorlage für die Einrichtung
*.template.md       Vorlagen für Schreibstil & Sender-Registry
```

Persönliche Daten (`config.json`, `voice/samples.md`, `senders.md`, `memory/`,
`runs/`) bleiben lokal und sind per `.gitignore` vom Versionieren ausgenommen.
Ausgeliefert werden nur die Vorlagen.

## Status

- ✅ Skill-Core, Gmail- und IMAP-Adapter nutzbar; IMAP inkl. DMARC-Prüfung.
- 🚧 Offen: native Microsoft-/Apple-Adapter (IMAP-Weg geht bereits).
