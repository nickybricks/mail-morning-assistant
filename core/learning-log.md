# Lernlog & Memory-Pflege

Das „Gedächtnis" des Assistenten liegt in `memory/email-assistant-memory.md` (pro Nutzer,
gitignored). Es ist ein **Lernlog**, kein Regelwerk: gespeichert werden
Entscheidungen + Begründungen, die das Modell beim nächsten Lauf als Kontext
mitliest — nicht ausführbare Regex.

## Aufbau der Memory-Datei

```markdown
# Email Assistant Memory

## User Profile
- Name, E-Mail, Sprache, Kontext (1 Satz), Zeitzone

## Provider
- provider: gmail | imap | microsoft | apple-mail
- Adapter-spezifische IDs (Gmail-Label-IDs, IMAP-Ordnernamen, …)

## Signature
- Aktuelle Signatur (formell/informell-Variante)

## Tone & Style Preferences
- Verweis auf voice/samples.md + Kernregeln (Du/Sie, Grußformeln, „LG"-Verbot etc.)

## Heim-Ordner
- Liste der angelegten Themen-Ordner + Status/Fallback

## VIP Senders
| Sender | Email | Kontext | Default-Aktion |

## Learning Log
| Datum | Sender/Pattern | Subject-Signal | Heimat / Lernen | Angewendet |
```

## Was wird gelernt

- **Sortier-Korrekturen.** Nutzer verschiebt Mail X → Sender+Subject-Pattern +
  Zielordner als Zeile festhalten. Beispiel: „`order@service.arket.com` mit
  Subject ‚Bestellung bestätigt' → Finanzen. Gelernt 2026-05-30."
- **Stil-Korrekturen.** Nutzer ändert Tonfall/Anrede in einem Entwurf → in
  „Tone & Style" bzw. `voice/samples.md` nachziehen.
- **VIP/Wichtig.** Nutzer markiert Sender als wichtig → VIP-Tabelle.
- **Neue Ordner.** Nutzer bestätigt neuen Themen-Ordner → Heim-Ordner-Liste.

## Pflege-Disziplin

- Am **Ende jedes Laufs** Memory aktualisieren: neue Lern-Einträge, Kosten-Eintrag.
- Memory **am Anfang jedes Laufs lesen**, bevor klassifiziert wird.
- Lernlog ist additiv; veraltete/widersprüchliche Einträge korrigieren statt
  doppeln.
- Memory enthält **keine Passwörter** und keine sensiblen Mailinhalte — nur
  Sortier-/Stil-Wissen.
