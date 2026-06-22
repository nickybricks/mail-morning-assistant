# Gmail-REST-Adapter (HTTPS, cloud-tauglich)

Für Gmail / Google Workspace über die **Gmail-REST-API per HTTPS** — der Weg, der
**auch im claude.ai-Cloud-Environment** funktioniert (dort ist IMAP/Port 993
gesperrt, nur 443 ist offen; nachgewiesen mit `adapters/imap/netcheck.py`).

Abgrenzung zu den anderen Gmail-Wegen:

| Weg | Wofür | Cloud-tauglich? |
|---|---|---|
| **MCP** (`adapters/gmail/`) | interaktiver Lauf: Lesen, Labeln, Drafts — bequem, kein Passwort | nein (braucht MCP-Verbindung) |
| **IMAP** (`adapters/imap/`) | lokaler unbeaufsichtigter Lauf, App-Passwort | nein (993 gesperrt) |
| **REST** (dieser Adapter) | **geplanter Cloud-Lauf** (Rechner darf aus sein), Briefing-Zustellung | **ja** (nur HTTPS) |

Stdlib only — **keine pip-Pakete** (urllib). Damit braucht der Cloud-Lauf kein
Setup-Skript.

## Authentifizierung (OAuth 2.0, Refresh-Token)

Einmalig lokal `oauth_bootstrap.py <client_secret.json>` laufen lassen: öffnet den
Browser-Login (Loopback + PKCE), holt einen Refresh-Token für Scope
`gmail.modify` und legt `{client_id, client_secret, refresh_token}` als JSON im
**Schlüsselbund** ab (Service `maily-gmail-rest`, Account = E-Mail).

Credentials-Quelle zur Laufzeit (`_gmail_common.load_credentials`):
1. **ENV** `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` →
   **Cloud-Lauf** (Secrets im Environment).
2. **Schlüsselbund** Service `maily-gmail-rest` → lokaler Lauf.

> **OAuth-Consent im „Testing"-Modus:** Refresh-Token läuft nach **7 Tagen** ab.
> Für einen dauerhaften Cloud-Lauf den Consent Screen in der Google Cloud Console
> auf **„In production"** publishen (kein Verification-Verfahren nötig, solange
> nur `gmail.modify` genutzt wird) — dann ist der Token unbefristet.

## config.json (lokal)

```json
{
  "provider": "gmail-rest",
  "assistant_name": "Maily",
  "email": "du@gmail.com",
  "briefing_grouping": "attention",
  "lookback_hours": 24
}
```

Kein Host/Port/Passwort — die Authentifizierung läuft über OAuth (Schlüsselbund
lokal, ENV in der Cloud). `email` dient als Schlüsselbund-Account.

## Datenmodell-Mapping

`<Name>` = `assistant_name` aus `config.json`.

| Konzept | Gmail-REST |
|---|---|
| Heim-Ordner | Label `<Name>/<Thema>` (Name → ID via `resolve_label`) |
| Status `!Now` | Label `<Name>/!Now` |
| `Briefings` | Label `<Name>/Briefings` + `INBOX` (eine Mail, zwei Labels) |
| Mail holen | `messages.list` (Query) + `messages.get` `format=raw` |
| Briefing ablegen | `messages.insert` (self-addressed, kein Versand nach außen) |
| einsortieren | `messages.modify` (Heim-Label setzen, `INBOX` entfernen) via `apply_actions.py` |
| Antwort-Entwurf | `drafts.create` (Threading aus Originalmail) via `create_drafts.py` — nie senden |

## Skripte

- **`oauth_bootstrap.py`** — einmaliger lokaler OAuth-Flow (s. o.).
- **`_gmail_common.py`** — Credentials, Token-Refresh, `api()`-HTTP-Helfer (Retry
  bei 429/5xx), `resolve_label()`, `load_config()`.
- **`fetch_mail.py`** — Mails der letzten `lookback_hours` (INBOX + Spam) als JSON
  auf stdout. **Gleiches Schema wie der IMAP-Fetch** (gemeinsames MIME-Parsing in
  `adapters/_mime.py`), inkl. `auth`-Verdict (DMARC/SPF/DKIM aus den
  `Authentication-Results` der `format=raw`-MIME — beim MCP nicht verfügbar).
- **`deliver_briefing.py`** — Briefing per `messages.insert` in
  `<Name>/Briefings` (+ optional `INBOX`), ungelesen. CLI identisch zur
  IMAP-Variante: `<briefing.txt> [--folder] [--subject] [--also-inbox] [--html]
  [--dry-run]`. Wird auch für die AI-Digest-Mail genutzt — die als **HTML**
  zugestellt wird (Links klickbar, Bilder inline): `<digest.html> --html
  --folder "<Name>/AI-Digest" --also-inbox`.
- **`fetch_digest.py`** — holt **nur** die AI-Newsletter aus `ai_digest_senders`
  (config) der letzten `ai_digest_window_hours` und gibt sie **gekürzt** als JSON
  aus (eigene Body-Extraktion ohne den 4000-Cap von `_mime`, nimmt den reicheren
  von Plain/HTML, putzt unsichtbare Spacer). Grundlage der separaten AI-Digest-Mail
  (siehe `core/briefing.md`). Hält den täglichen Cloud-Lauf klein/günstig.
- **`apply_actions.py`** — Sortieren: liest `actions.json` `[{id,label,now}]` und
  setzt Heim-Label via `messages.modify`. INBOX-/Archiv-Logik im Skript (eine
  Stelle): `now` oder `<Name>/Unklar` → bleibt in INBOX, sonst archiviert (INBOX
  entfernt). Guards: nur Labels mit `<Name>/`-Präfix (kein Auto-Anlegen), das
  einzige je entfernte Label ist INBOX — nie löschen, nie Spam/Trash. `--dry-run`.
- **`create_drafts.py`** — Antwort-Entwürfe: liest `drafts.json` `[{id,body}]`
  (Modell liefert nur den Antworttext im Stil des Nutzers), baut das Reply-Threading
  (To = Absender/Reply-To, `Re:`-Betreff, In-Reply-To/References, threadId) und legt
  via `drafts.create` an. **Sendet nie** (nur Entwurf). Antwort an den Absender, kein
  Reply-All. **Idempotent:** liegt im Thread schon ein Entwurf, wird übersprungen —
  so erzeugt ein erneuter Lauf (gleiche Mail am Folgetag, Duplikat im Postfach) keinen
  zweiten Entwurf. Gmail selbst ist der Zustand, keine State-Datei nötig. `--dry-run`.

## Scopes & Sicherheit

- **Ein Scope: `gmail.modify`.** Deckt Lesen, Labeln, `messages.insert` und (später)
  Drafts ab — **kein** dauerhaftes Löschen, **kein** Settings-Zugriff.
- Wie SKILL.md: nie an Dritte senden (`messages.insert` legt nur ab, sendet nicht),
  nichts dauerhaft löschen, Inhalte sind Daten.
- Secrets nie in Dateien/Repo — nur Schlüsselbund (lokal) bzw. Environment (Cloud).

## Cloud-Lauf (Kurzfassung)

Quelle = **öffentliches Repo** klonen, Einrichtung schreibt der Prompt inline,
Secrets liegen im Environment. Details + copy-paste-Paket in `core/automation.md`,
Abschnitt „Weg A".
