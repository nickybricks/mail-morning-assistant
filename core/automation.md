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

## ⚠️ Getestet 2026-05-31: claude.ai-Cloud ist HTTPS-only → kein IMAP

In einem echten Cloud-Lauf gemessen (`adapters/imap/netcheck.py`): Das claude.ai-
Cloud-Environment lässt **nur HTTPS (443)** nach außen — **IMAP (Port 993) ist
gesperrt** (`Errno 97`/Timeout), **auch** bei Netzwerkzugriff „Vertraut". Das ist
eine **Plattform-Grenze, nicht über Einstellungen lösbar.**

**Konsequenz:** Eine **claude.ai-Routine kann KEIN IMAP** → der unten beschriebene
Weg A funktioniert für IMAP **nicht**. Für „läuft, wenn der Rechner aus ist"
braucht es einen Weg, der **über HTTPS** auf die Mails kommt:

| Anbieter | Cloud-Weg (HTTPS, Rechner darf aus sein) |
|---|---|
| **Gmail / Workspace** | **Google Apps Script** (läuft auf Googles Servern, scheduled Trigger, voller Mailzugriff inkl. Ablegen/Labeln) — das ist der saubere Weg. Alternativ Gmail-REST-API per OAuth. |
| **Microsoft 365** | MS Graph API (HTTPS) |
| **Reines IMAP** (all-inkl, GMX, …) | claude.ai-Cloud geht **nicht**; nur **eigener Server/Cron** (Weg B) oder ein Rechner, der läuft. |

Der **lokale** Betrieb (interaktiv + lokaler Zeitplan, Rechner an) ist davon
**nicht** betroffen — IMAP funktioniert dort normal.

## Scheduler — Wege (Nutzer wählt, was passt)

### A) claude.ai-Routine — NUR für HTTPS-basierte Zugänge (NICHT IMAP)

> **Achtung:** Wegen der HTTPS-only-Grenze (oben) ist dieser Weg **nicht** für
> IMAP nutzbar. Tauglich nur, wenn der Mailzugriff über eine **HTTPS-API**
> erfolgt (z. B. ein künftiger Gmail-API-/Graph-Adapter). Für Gmail heute lieber
> Apps Script (siehe Tabelle).

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

#### Schritt für Schritt in claude.ai (für komplette Einsteiger — idiotensicher)

Der Assistent führt den Nutzer **Feld für Feld** durch und nimmt nichts als
bekannt an. Wortlaut etwa so:

1. **Hinkommen:** „Öffne **claude.ai/code** (etwas versteckt: oben/Menü →
   *Code*). Dort links **Routines** → **Neue Routine**."
2. **Name*** → Vorschlag: `<Name> – Morgen-Mail-Briefing`.
3. **Anweisungen** → „Das ist der Auftrag (Prompt). Füge **genau diesen Text**
   ein:" → der **individuell erzeugte Prompt** (siehe oben; mit Name/Host/E-Mail
   des Nutzers schon eingesetzt).
4. **Modell** (kleines Dropdown unten rechts im Anweisungen-Feld) → **Sonnet**
   wählen. „Reicht locker und ist günstig für einen täglichen Lauf."
5. **Quelle** (das `+`/Repo-Feld) → die **öffentliche Repo-URL** einfügen:
   `https://github.com/<org>/mail-morning-assistant`. „Kein Login nötig, ist
   öffentlich."
6. **Zeitplan** → Reiter **Täglich** + Uhrzeit (Vorschlag früh morgens, z. B.
   06:57). „Für stündlich/Werktage die anderen Reiter — dann sag mir die Frequenz,
   ich passe `lookback_hours` an."
7. **Konnektoren** → **alle entfernen.** „Dieser Assistent braucht keine — er
   arbeitet über IMAP. Connectors hätten sonst vollen Schreibzugriff."
8. **Berechtigungen/Verhalten** → sicherstellen, dass **Bash** + Datei lesen/
   schreiben erlaubt sind.
9. **Cloud-Umgebung anlegen** (Dialog „Neue Cloud-Umgebung"):
   - **Name** = z. B. `<Name>` — **NICHT** das Passwort (häufiger Fehler!).
   - **Netzwerkzugriff** = **Vertraut** — sonst kein Zugriff auf den Mailserver.
   - **Umgebungsvariablen** = eine Zeile, **nur das Passwort, ohne spitze Klammern**:
     `MAIL_IMAP_PASSWORD=<das App-Passwort>`. Hinweis: Umgebung **privat** halten.
   - **Setup-Skript** leer lassen.
10. **Erstellen.** Empfehlung: erst **einen Testlauf** (manuell), prüfen ob das
    Briefing in `<Name>/Briefings` ankommt; dann aktiviert lassen.

> Diese Maske ändert sich gelegentlich. Wenn ein Feldname nicht passt, das
> nächstgelegene sinngemäß nehmen und den Nutzer fragen — nie raten bei Secret/
> Netzwerk.

### B) Cron auf einem immer-laufenden Rechner/Server

Wenn ein eigener Server/NAS o. Ä. dauerhaft läuft, reicht klassischer Cron, der
die Skripte direkt aufruft (kein Claude-Modell nötig für fetch/deliver; die
Klassifikation/Brief-Texte würde ein separater Modell-Aufruf erzeugen):

```
# 6:57 täglich, Passwort aus der Umgebung
57 6 * * *  cd /pfad/zum/skill && MAIL_IMAP_PASSWORD=… python3 adapters/imap/fetch_mail.py > /tmp/mail.json && … 
```
(Hier ist eigene Glue-Logik nötig, die fetch → Klassifikation/Brief → deliver
verbindet.)

### C) Gmail Apps Script (empfohlen für Gmail, wenn der Rechner aus sein soll)

Für **Gmail/Workspace** der sauberste „läuft auch bei ausgeschaltetem Rechner"-Weg:
ein Google **Apps Script** mit Zeit-Trigger läuft auf Googles Servern, hat vollen
Mailzugriff (lesen, labeln, eine Briefing-Mail anlegen) und unterliegt **keiner**
Port-Sperre. Kein IMAP, kein claude.ai-Environment nötig. (Setup-Hilfe: separates
Apps-Script-Rezept / die „gmail-morning-assistant"-Vorlage.)

## Empfehlung (nach dem HTTPS-only-Test)

- **Rechner läuft sowieso / nur lokal gewünscht:** lokaler Zeitplan, IMAP-Adapter,
  voll funktionsfähig.
- **Rechner darf aus sein + Gmail:** **Apps Script** (Weg C).
- **Rechner darf aus sein + reines IMAP-Postfach:** eigener Server/Cron (Weg B).
- **claude.ai-Routine (Weg A):** erst sinnvoll, wenn ein **HTTPS-API-Adapter**
  existiert (Gmail-API/Graph) — mit dem heutigen IMAP-Adapter **nicht** nutzbar
  (HTTPS-only-Grenze, getestet).
