# Automatischer Modus — der tägliche Lauf ohne Mensch

Der Assistent läuft in **zwei Modi**:

- **Interaktiv** — der Nutzer öffnet Claude Code, sagt „Start", sieht das Briefing
  im Chat, gibt vor dem scharfen Lauf sein OK. (Standard, siehe SKILL.md.)
- **Automatisch** — ein Scheduler startet den Lauf zu fester Zeit (z. B. 7:00),
  **ohne dass jemand zusieht**. Das Briefing landet als Mail in
  `<assistant_name>/Briefings`. Ersetzt klassische „Morgenmail"-Routinen.

Dieser Text beschreibt den automatischen Modus **scheduler- und anbieter-agnostisch**.

## Woher kommen die Dateien? (Lokal vs. Cloud)

Wichtig — das entscheidet, ob ein Repo nötig ist:

- **Lokal (Normalfall):** Skill + Einrichtung liegen im **lokalen Ordner** des
  Nutzers. Interaktive Läufe und auf dem **eigenen, eingeschalteten Rechner**
  geplante Läufe (z. B. Claude-Code-`/schedule`, lokaler Cron) lesen direkt von
  dort. **Kein Repo nötig.** Nachteil: läuft nur, wenn der Rechner an ist.
- **Cloud (Rechner darf aus sein):** Der Lauf passiert auf einem **fremden
  Server** (claude.ai-Routine), der den lokalen Ordner nicht sieht. Darum müssen
  Skill **und** Einrichtung für den Server erreichbar sein — typisch über ein
  **(privates) Git-Repo**, plus das Postfach-Passwort als Secret. Das Repo ist
  also **nur** die Brücke für den Cloud-Fall, kein Teil der normalen Nutzung.

Faustregel: „Soll es laufen, wenn mein Rechner aus ist?" → Cloud (Repo). Sonst →
lokal (kein Repo).

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

Eine geplante Remote-Routine führt Claude Code in der Cloud aus. **Kein privates
Repo nötig:** die Routine klont das **öffentliche** Skill-Repo; die nicht-geheime
Einstellung schreibt der Lauf selbst (per Prompt), und das Postfach-Passwort liegt
als **Secret** im Environment. Der Nutzer legt **kein Repo an und schreibt keinen
Code** — er füllt einmal die Routine-Maske in claude.ai aus.

> **Verifizierter Vorbehalt:** Die Routine braucht zwingend ein **Environment**
> mit dem Secret — das wird **einmalig in der claude.ai-Oberfläche** angelegt
> (lässt sich nicht aus dem Chat heraus erstellen). Das ist der einzige Schritt
> außerhalb des Chats. Der Assistent liefert dafür ein **copy-paste-fertiges
> Paket**:

**Copy-paste-Paket (Platzhalter `<…>` ausfüllen):**

- **Quelle (Repo, öffentlich):** `https://github.com/<org>/mail-morning-assistant`
- **Zeitplan (Cron, lokale Zeit):** z. B. `57 6 * * *`
- **Modell:** ein Sonnet-Modell
- **Erlaubte Tools:** `Bash`, `Read`, `Write`
- **Secret:** `MAIL_IMAP_PASSWORD` = das IMAP-App-Passwort
- **Prompt:**
  ```
  Du läufst in einem Klon des öffentlichen Repos mail-morning-assistant
  (Arbeitsverzeichnis = Repo-Wurzel). Automatischer Morgenlauf — NUR Briefing,
  kein Sortieren/Verschieben/Löschen, kein Versand an Dritte.

  1. Schreibe config.json ins Wurzelverzeichnis:
     {"provider":"imap","assistant_name":"<Name>","imap_host":"<host>",
      "imap_port":993,"email":"<email>","briefing_grouping":"attention",
      "lookback_hours":24,"drafts_folder":null}
     Das Passwort steht in ENV MAIL_IMAP_PASSWORD; fehlt sie -> abbrechen + im Log melden.
  2. python3 adapters/imap/fetch_mail.py  (Mails der letzten 24h; nur folder=="INBOX" fürs Briefing)
  3. Lies core/briefing.md. Schreibe das Briefing (Gruppierung attention,
     ein Satz pro Mail, Newsletter≠Müll, Kosten-Footer) nach briefing.txt.
  4. python3 adapters/imap/deliver_briefing.py briefing.txt --folder "<Name>/Briefings" --also-inbox
  5. Log: Anzahl Mails + ob Zustellung ok.

  EISERN: nichts senden außer dem eigenen Briefing (APPEND), nichts löschen,
  kein Spam/Papierkorb, keine Drafts. Bei Fehler klar melden, nichts raten.
  ```

Erster Lauf am besten **manuell/deaktiviert testen** (prüfen, ob das Environment
IMAP nach außen erreichen darf), dann aktivieren. Sortieren/Drafts im Auto-Modus
erst ergänzen, wenn die Lernlog-Memory auch in der Cloud verfügbar ist.

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
