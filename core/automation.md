# Automatischer Modus — der tägliche Lauf ohne Mensch

Der Assistent läuft in **zwei Modi**:

- **Interaktiv** — der Nutzer öffnet Claude Code, sagt „Start", sieht das Briefing
  im Chat, gibt vor dem scharfen Lauf sein OK. (Standard, siehe SKILL.md.)
- **Automatisch** — ein Scheduler startet den Lauf zu fester Zeit (z. B. 7:00),
  **ohne dass jemand zusieht**. Das Briefing landet als Mail in
  `<assistant_name>/Briefings`. Ersetzt klassische „Morgenmail"-Routinen.

Dieser Text beschreibt den automatischen Modus **scheduler- und anbieter-agnostisch**.

## Voraussetzungen (für jeden Nutzer gleich)

1. **Unbeaufsichtigte Zustellung → IMAP.** Im Auto-Modus muss der Lauf selbst
   eine Mail ablegen können. Das geht über **IMAP** (`deliver_briefing.py`), nicht
   über OAuth/MCP. Auch Gmail/Outlook werden hier über IMAP bedient
   (`adapters/imap/` + provider-spezifischer Host/App-Passwort).
2. **Passwort als Secret/Umgebungsvariable.** Kein Schlüsselbund im Cloud-/Server-
   Lauf → das IMAP-App-Passwort kommt als `MAIL_IMAP_PASSWORD` aus der
   Umgebung (vom Code bereits unterstützt).
3. **Eingerichtete `config.json` + `memory/`** müssen dem Lauf vorliegen
   (lokal im Repo/Verzeichnis, das der Scheduler nutzt).

## Ablauf je automatischem Lauf

Wie SKILL.md „Tagesablauf", aber **ohne Vorschau-Schritt** (kein Mensch da):

1. Memory + Adapter laden.
2. `fetch_mail.py` — Mails der letzten 24h (Fokus INBOX) holen.
3. Klassifizieren (`core/classification.md`), Briefing schreiben
   (`core/briefing.md`, mit Kosten-Footer).
4. Sortieren/Flaggen direkt ausführen — **konservativ** (siehe Sicherheit unten).
5. Briefing per `deliver_briefing.py` in `<assistant_name>/Briefings` ablegen
   (optional `--also-inbox`).
6. Memory aktualisieren (Lernlog, Kosten).

## Sicherheit im Auto-Modus (strenger, weil niemand zusieht)

- **Nie an Dritte senden, nie löschen, kein Spam/Papierkorb leeren** — wie immer.
- **Konservativ sortieren:** nur bei hoher Confidence in einen Heim-Ordner; alles
  Unsichere → `Unklar`/INBOX, damit der Nutzer es beim nächsten Blick sieht.
- **Keine Drafts an Dritte verschicken** — Entwürfe bleiben Entwürfe.
- Der einmal im Onboarding abgestimmte Standard gilt; größere Änderungen
  (neue Ordner) sammelt der Lauf und schlägt sie beim nächsten **interaktiven**
  Lauf vor, statt sie unbeaufsichtigt anzulegen.

## Frequenz & Tage — frei wählbar

Der Nutzer bestimmt, **wie oft** und **an welchen Tagen** gelaufen wird — per
Cron-Ausdruck (lokale Zeit). Beispiele:

| Wunsch | Cron |
|---|---|
| Jeden Morgen ~7:00 | `57 6 * * *` |
| Stündlich | `7 * * * *` |
| Alle 2 / 3 / 4 Stunden | `0 */2 * * *` · `0 */3 * * *` · `0 */4 * * *` |
| Nur Werktage morgens | `57 6 * * 1-5` |
| Nur Mo/Mi/Fr | `57 6 * * 1,3,5` |

> **Zeitfenster an die Frequenz koppeln (wichtig!):** Läuft der Assistent
> stündlich, darf er nicht die letzten 24 h zusammenfassen — sonst wiederholt
> sich alles. Das Fenster steuert `lookback_hours` in `config.json` (oder ENV
> `MAIL_LOOKBACK_HOURS`): stündlich → `1`, alle 3 h → `3`, täglich → `24`.
> Faustregel: `lookback_hours` = Abstand zwischen zwei Läufen.

Im Onboarding (Schritt 6) wird beides abgefragt; Default = täglich morgens, 24 h.

## Scheduler — zwei Wege (Nutzer wählt, was er hat)

### A) claude.ai-Routine (Cloud — läuft, auch wenn der Rechner aus ist)

Eine geplante Remote-Routine führt Claude Code in der Cloud aus. Sie zieht ihren
Kontext aus einem **Git-Repo**; das Postfach-Secret liegt im Cloud-Environment.

- Skill in ein **Git-Repo** legen (ohne persönliche Daten — `.gitignore` greift;
  `config.json`/`memory/` müssen für den Lauf aber verfügbar sein, also entweder
  ein **privates** Repo mit der Instanz oder Environment-seitig bereitgestellt).
- Routine: Cron (lokale Zeit, z. B. `57 6 * * *`), Modell, erlaubte Tools
  (`Bash`, `Read`, `Write`), Quelle = das Repo.
- Secret `MAIL_IMAP_PASSWORD` im Environment hinterlegen (claude.ai-Oberfläche).
- Prompt (sinngemäß): „Führe den Morgen-Mail-Assistenten aus: lies die INBOX der
  letzten 24h über IMAP, klassifiziere, schreibe das Briefing und lege es per
  `adapters/imap/deliver_briefing.py` in `<Name>/Briefings`. Kein Versand an
  Dritte, nichts löschen."

### B) Cron auf einem immer-laufenden Rechner/Server

Wenn ein eigener Server/NAS o. Ä. dauerhaft läuft, reicht klassischer Cron, der
die Skripte direkt aufruft (kein Claude-Modell nötig für fetch/deliver; die
Klassifikation/Brief-Texte würde ein separater Modell-Aufruf erzeugen):

```
# 6:57 täglich, Passwort aus der Umgebung
57 6 * * *  cd /pfad/zum/skill && MAIL_IMAP_PASSWORD=… python3 adapters/imap/fetch_mail.py > /tmp/mail.json && … 
```
(Hier ist eigene Glue-Logik nötig, die fetch → Klassifikation/Brief → deliver
verbindet. Für die meisten Nutzer ist Weg A einfacher.)

## Empfehlung

Für „läuft morgens automatisch, auch wenn der Rechner aus ist" ist **Weg A**
(claude.ai-Routine) der einfachste. Weg B ist für Selbst-Hoster mit eigenem Server.
