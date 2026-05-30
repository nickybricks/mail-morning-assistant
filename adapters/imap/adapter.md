# IMAP-Adapter

Für klassische Postfächer per IMAP: **all-inkl, IONOS/1&1, web.de, GMX, Strato,
mailbox.org, Hetzner** und beliebige andere. Ordner = Heim-Ordner,
`\Flagged` = Status `!Now`, Drafts-Ordner = Entwürfe (erscheinen automatisch im
Mailprogramm des Nutzers, z. B. Apple Mail / Thunderbird).

## Datenmodell-Mapping

`<Name>` = im Onboarding gewählter Assistenten-Name (`config.json` →
`assistant_name`; z. B. `Maily`). Heim-Ordner werden darunter angelegt.

| Konzept | IMAP |
|---|---|
| Heim-Ordner | IMAP-Ordner `<Name>/<Thema>` (ggf. `INBOX.<Name>.<Thema>` bei Dovecot) |
| Status `!Now` | `\Flagged` |
| `Unklar` / `Briefings` | eigene Ordner, bleiben in Inbox sichtbar via Kopie |
| Entwurf | Append in Drafts-Ordner mit `(\Draft)` |

## Onboarding (Schritt 1 aus core/onboarding.md)

Der Assistent fragt **nicht** nach kryptischen Hostnamen. Stattdessen
Provider-Karten; Host/Port kommen aus den Presets unten. Nur bei „Anderer
Anbieter" wird der Host erfragt.

### Provider-Presets

| Anbieter | imap_host | Port | App-Passwort? |
|---|---|---|---|
| all-inkl.com | `<dein>.kasserver.com` (steht im KAS-Login) | 993 | nein, normales Postfach-PW |
| IONOS / 1&1 | `imap.ionos.de` | 993 | nein |
| web.de | `imap.web.de` | 993 | **ja** — „POP3/IMAP" erst in den Einstellungen aktivieren |
| GMX | `imap.gmx.net` | 993 | **ja** — IMAP-Zugriff in Einstellungen aktivieren |
| Strato | `imap.strato.de` | 993 | nein |
| mailbox.org | `imap.mailbox.org` | 993 | empfohlen App-Passwort |
| Hetzner | `imap.your-server.de` | 993 | nein |
| Anderer | nach Host fragen (oft `imap.<domain>`) | 993 | im Zweifel ja |

> all-inkl-Hinweis: Der Host ist nutzerspezifisch (`wXXXXXXX.kasserver.com`) und
> steht im KAS-Adminbereich unter „E-Mail". Der Assistent fragt danach in einfachen Worten.

### App-Passwort erklären (für Nicht-Techniker)

Wenn der Anbieter ein App-Passwort verlangt, erklärt der Assistent knapp:
> „Dein Anbieter will aus Sicherheitsgründen ein eigenes Passwort nur für
> Programme wie mich — dein normales Login-Passwort funktioniert hier nicht.
> Das legst du einmal in den Konto-Einstellungen deines Anbieters an
> (Stichwort ‚App-Passwort' oder ‚IMAP aktivieren'). Ich sag dir, wo."

### Passwort sicher ablegen (macOS-Schlüsselbund)

Das Passwort kommt **nie** in eine Datei. Auf macOS in den Schlüsselbund legen
(der Assistent führt den Befehl vor, bittet den Nutzer ihn auszuführen — oder
nutzt für einen Testlauf `MAIL_IMAP_PASSWORD` als Umgebungsvariable):

```
security add-generic-password -s "mail-imap" -a "DEINE@EMAIL.de" -w
```
(Das Terminal fragt das Passwort dann verdeckt ab.)

### config.json schreiben

```json
{
  "provider": "imap",
  "assistant_name": "Maily",
  "imap_host": "imap.ionos.de",
  "imap_port": 993,
  "email": "du@deine-domain.de",
  "keychain_service": "mail-imap",
  "drafts_folder": null,
  "voice_samples_path": "voice/samples.md"
}
```

## Tägliche Operationen

**Mails der letzten 24h holen** (liest INBOX + alle Unterordner, markiert nichts
als gelesen, verändert nichts; Spam wird mitgelesen und mit `is_spam: true`
markiert, aber nichts herausgeholt):
```
python3 adapters/imap/fetch_mail.py
```
Ausgabe: JSON `{ "count": N, "emails": [...] }`. Bei `error`-Feld: dem Nutzer
konkret sagen was fehlt, stoppen.

**Sortieren / Flaggen / Entwürfe ablegen** — Plan als `plan.json`, dann:
```
python3 adapters/imap/save_drafts.py plan.json [--dry-run]
```
`plan.json`:
```json
{
  "drafts": [
    {"to": "...", "subject": "Re: ...", "body": "...",
     "in_reply_to": "<id>", "references": "<id> <id>"}
  ],
  "actions": [
    {"uid": "123", "folder": "INBOX", "flag": true},
    {"uid": "456", "folder": "INBOX", "move_to": "Finanzen"}
  ]
}
```
`folder` ist Pflicht, sobald die Mail in einem Unterordner liegt (UIDs sind pro
Ordner eindeutig, nicht global). `move_to` legt den Zielordner bei Bedarf an und
ordnet ihn bei Dovecot-Servern automatisch unter `INBOX.` ein. **Beim ersten
scharfen Lauf immer `--dry-run` zuerst** und mit dem Nutzer bestätigen.

**Briefing als Mail an den Nutzer selbst ablegen** (per `APPEND`, kein SMTP-
Versand — die Mail wird nur lokal ins Postfach gelegt):
```
python3 adapters/imap/deliver_briefing.py briefing.txt \
        [--folder "<Name>/Briefings"] [--subject "..."] [--also-inbox] [--dry-run]
```
- Default-Ordner: `<assistant_name>/Briefings`; Default-Betreff: `<Name>-Briefing — <Datum>`.
- Self-addressed (From/To = eigene Adresse), als **ungelesen** abgelegt.
- `--also-inbox` legt zusätzlich eine Kopie in INBOX (morgens sichtbar).
- Ordnernamen werden modified-UTF-7-kodiert; nicht existierende Ordner werden angelegt.

## DMARC / SPF / DKIM (implementiert — für IMAP besonders wertvoll)

IMAP-Server filtern Spam oft schwächer als Gmail. `fetch_mail.py` parst die
`Authentication-Results`-Header (die der empfangende Server setzt) und gibt pro
Mail ein `auth`-Feld aus:

```json
"auth": { "dmarc": "fail", "spf": "softfail", "dkim": "fail", "verdict": "suspicious" }
```

`verdict` (konservativ, lieber unter- als überflaggen):

| verdict | Bedeutung | im Briefing |
|---|---|---|
| `pass` | mind. ein starkes Signal besteht (dmarc/spf/dkim = pass) | nichts |
| `suspicious` | DMARC=fail **oder** SPF und DKIM beide versagen | ⚠️ deutlich markieren |
| `weak` | kein starker Pass, Signale fehlen/none (z. B. Domain ohne DMARC) | leise erwähnen, nur wenn Inhalt schon verdächtig |
| `unknown` / `auth: null` | kein/unklarer Header (manche Server setzen keinen) | nichts — **kein** Verdacht |

**Nie automatisch in Spam verschieben** — auch bei `suspicious` nur im Briefing
flaggen und den Nutzer entscheiden lassen (schützt den Lerneffekt des
Server-Filters). Die Auth-Heuristik ergänzt die inhaltliche Phishing-Prüfung aus
`core/briefing.md`, ersetzt sie nicht.

## Ordnernamen (Emoji/Umlaute)

IMAP überträgt Ordnernamen in „modified UTF-7" (RFC 3501), z. B. `Privat/Amazon
&2D3c5g-` für `Privat/Amazon 📦`. Der Adapter dekodiert das automatisch:
`fetch_mail.py` gibt **lesbare** Namen im `folder`-Feld aus, `save_drafts.py`
**enkodiert** `folder`/`move_to` aus dem Plan vor `SELECT`/`MOVE`/`CREATE` zurück.
In Briefing und Plan also immer die lesbaren Namen (mit Emoji/Umlaut) verwenden —
um die Kodierung kümmert sich der Adapter (`imap_utf7_decode`/`_encode` in
`_imap_common.py`).

## Portabilität über Anbieter

`fetch_mail.py` ist anbieter-robust gebaut:
- **Trennzeichen** wird aus der `LIST`-Antwort gelesen (`/` bei 1und1, `.` bei
  vielen Dovecot-Servern, `NIL` ohne Hierarchie) — nicht angenommen.
- **System-Ordner** (Gesendet/Entwürfe/Papierkorb) werden primär über die
  `\Sent`/`\Drafts`/`\Trash`/`\Archive`-Flags (RFC 6154, sprachunabhängig)
  übersprungen, ersatzweise über eine enge DE/EN-Namensliste. **„Archiv" wird
  nie per Name übersprungen** (nur per `\Archive`-Flag), weil viele User dort
  echte Mail (z. B. Newsletter) ablegen — im Zweifel lieber zeigen als verstecken.

## Grenzen

- Liest nur INBOX + Unterordner; Papierkorb/Entwürfe/Gesendet/Archiv werden
  übersprungen, Spam nur gelesen, nie geleert.
- Kein OAuth — Anbieter mit erzwungenem OAuth (z. B. manche Microsoft-Tenants)
  besser über den `microsoft`-Adapter.
