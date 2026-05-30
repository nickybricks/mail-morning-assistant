# Apple-Mail-Adapter — STUB (noch nicht implementiert)

Für iCloud-Mail bzw. ein lokales Apple-Mail-Setup. Geplant, aber noch nicht gebaut.

## Geplanter Ansatz

Zwei Wege:

1. **IMAP** (am einfachsten und empfohlen) — iCloud spricht IMAP
   (`imap.mail.me.com`, Port 993) und **verlangt ein App-spezifisches Passwort**
   (appleid.apple.com → Anmeldung & Sicherheit → App-spezifische Passwörter).
   Dann den `imap`-Adapter nutzen. Entwürfe im IMAP-Drafts-Ordner erscheinen
   automatisch in Apple Mail.
2. **Lokal via AppleScript** (nur macOS, nur wenn IMAP nicht gewünscht) —
   Apple Mail direkt steuern: Postfächer lesen, Nachrichten in Postfächer
   verschieben, Flags setzen, Entwürfe anlegen. Vorteil: keine Server-Zugangsdaten
   nötig, nutzt das eingerichtete Konto. Nachteil: an macOS + laufendes Mail.app
   gebunden, langsamer, fragiler.

## Bis dahin

Beim Onboarding standardmäßig den **IMAP-Weg** anbieten (iCloud-Host + Hinweis
auf App-spezifisches Passwort). Der AppleScript-Weg ist ein späterer Ausbau für
Nutzer, die kein App-Passwort anlegen wollen.

## Datenmodell-Mapping (Zielbild, IMAP)

| Konzept | Apple Mail / iCloud-IMAP |
|---|---|
| Heim-Ordner | Postfach/Ordner |
| Status `!Now` | Flagge (`\Flagged`) |
| Entwurf | Drafts-Ordner |
