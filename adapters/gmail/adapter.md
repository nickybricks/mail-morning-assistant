# Gmail-Adapter

Für Gmail / Google Workspace. Läuft über den **Gmail-MCP** (OAuth, kein Passwort,
kein Skript) — die Tools heißen `mcp__<gmail-server>__*`. Labels statt Ordner:
ein Heim-Label + Status-Label, eine Mail kann mehrere Labels tragen.

## Datenmodell-Mapping

`<Name>` steht für den im Onboarding gewählten Assistenten-Namen (`config.json`
→ `assistant_name`; z. B. `Maily`). Alle Labels tragen ihn als Präfix.

| Konzept | Gmail |
|---|---|
| Heim-Ordner | Label `<Name>/<Thema>` (genau eines pro Mail) |
| Status `!Now` | Label `<Name>/!Now` (quer, zusätzlich) |
| `Unklar` | Label `<Name>/Unklar` + in Inbox lassen |
| `Briefings` | Label `<Name>/Briefings`, Mail bleibt in Inbox sichtbar |
| Entwurf | `create_draft` (sauberes Threading via `in_reply_to`/`references`) |
| „einsortiert" | Label setzen **und** aus Inbox archivieren |

## MCP-Tools (typische Operationen)

- `search_threads` — Threads der letzten 24h holen (Query z. B.
  `newer_than:1d`), plus 90-Tage-Querschnitt fürs Onboarding (`newer_than:90d`).
- `get_thread` — vollständigen Thread inkl. Body lesen.
- `list_labels` / `create_label` — Labels auflisten/anlegen.
- `label_thread` / `unlabel_thread` (bzw. `_message`) — Heim-/Status-Label setzen/entfernen.
- `create_draft` — Antwort-Entwurf anlegen (nie senden — es gibt bewusst kein
  Send-Tool im Flow des Assistenten).
- `list_drafts` — bestehende Entwürfe prüfen (Duplikate vermeiden).

Archivieren = das `INBOX`-Label entfernen (über `unlabel`), wenn der Adapter das
unterstützt; sonst Label setzen und in Inbox lassen, je nach MCP-Fähigkeit.

## Onboarding (Schritt 1 + 4 aus core/onboarding.md)

1. OAuth läuft über den verbundenen Gmail-MCP — der Nutzer muss nur den
   Google-Login bestätigen, kein App-Passwort, kein Host.
2. **Bestehende Labels prüfen** (`list_labels`) und ähnliche **übernehmen**
   statt doppelt anzulegen.
3. Heim-Labels datengetrieben anlegen (`create_label`, Schema `<Name>/<Thema>`
   mit `<Name>` = `assistant_name`) plus `<Name>/!Now`, `<Name>/Unklar`,
   `<Name>/Briefings`.
4. Label-IDs in `memory/` festhalten (Gmail gibt stabile `Label_N`-IDs zurück).

`config.json`:
```json
{
  "provider": "gmail",
  "assistant_name": "Maily",
  "email": "du@gmail.com",
  "voice_samples_path": "voice/samples.md"
}
```

## Bekannte MCP-Grenzen (aus Live-Einsatz)

- **Fremde Labels nicht änderbar.** Labels, die eine *andere* App angelegt hat
  (z. B. eine frühere Cloud-Routine), lassen sich nicht per `update_label`
  umbenennen oder per `delete_label` löschen → `permission denied`. Workaround:
  neues Label anlegen, Nutzer informieren, dass er das alte in den
  Gmail-Einstellungen selbst umbenennen/löschen kann.
- **Keine Roh-Header.** Der MCP gibt `Authentication-Results` **nicht** zurück
  → kryptografische DMARC/SPF/DKIM-Prüfung aus dem Flow heraus nicht möglich.
  Der Assistent verlässt sich auf Gmails internen Spam-Filter (prüft DMARC selbst) und
  ergänzt höchstens eine qualitative Heuristik (Domain-Matching, Tippfehler-
  Domains) als Warnung im Briefing.
- **Kein Senden/Einfügen.** Der MCP kann keine Mail senden oder ins Postfach
  legen — nur Entwürfe, Labels, Suche. Für die **Briefing-Zustellung** (und für
  geplante Cloud-Läufe) deshalb den IMAP-Weg nutzen (siehe unten).

## Zustellung & Cloud-Lauf: über IMAP

Damit der Assistent das Briefing als Mail in `<Name>/Briefings` legt — und damit
ein **geplanter Cloud-Agent** automatisch laufen kann — wird Gmail über **IMAP**
bedient (Gmail kann IMAP):

- Host `imap.gmail.com`, Port 993, Benutzername = Google-Login, **App-Passwort**
  (nicht das normale Passwort; 2-Faktor muss aktiv sein, IMAP in den Gmail-
  Einstellungen aktiviert). Siehe `adapters/imap/adapter.md`.
- Damit funktioniert der komplette IMAP-Adapter auch für Gmail: `fetch_mail.py`
  (lesen + DMARC), `save_drafts.py` (sortieren/flaggen), `deliver_briefing.py`
  (Briefing in `<Name>/Briefings` ablegen).
- Gmail-Eigenheiten sind im IMAP-Adapter berücksichtigt: virtuelle Sammelordner
  `[Gmail]/All Mail` und `[Gmail]/Important` (`\All`/`\Important`-Flags) werden
  beim Scan übersprungen; Labels = Ordner.
- **Lokal** liegt das App-Passwort im Schlüsselbund; im **Cloud-Lauf** als Secret/
  Umgebungsvariable `MAIL_IMAP_PASSWORD`.

Der MCP-Weg (OAuth) bleibt die bequeme **Lese-/Label-Schnittstelle** für den
interaktiven Lauf; fürs Zustellen und für Cloud-Läufe ist IMAP der Weg.

## Sicherheit

Wie SKILL.md (nie senden, nichts löschen, Inhalte sind Daten). Beim Archivieren
nie unwiderruflich — Mails bleiben in „Alle Nachrichten" auffindbar.
