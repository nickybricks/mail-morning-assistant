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

## Cost Ledger
| Datum | Modell(e) | Token rein | Token raus | Kosten ($) |
```

## Was wird gelernt

- **Sortier-Korrekturen.** Nutzer verschiebt Mail X → Sender+Subject-Pattern +
  Zielordner als Zeile festhalten. Beispiel: „`order@service.arket.com` mit
  Subject ‚Bestellung bestätigt' → Finanzen. Gelernt 2026-05-30."
- **Stil-Korrekturen.** Nutzer ändert Tonfall/Anrede in einem Entwurf → in
  „Tone & Style" bzw. `voice/samples.md` nachziehen.
- **VIP/Wichtig.** Nutzer markiert Sender als wichtig → VIP-Tabelle.
- **Neue Ordner.** Nutzer bestätigt neuen Themen-Ordner → Heim-Ordner-Liste.

## Cost Ledger — kumulierte Kosten

Damit das Briefing nicht nur die Kosten *dieses* Laufs, sondern auch die
auflaufende Summe zeigen kann (siehe `core/briefing.md`), führt der Assistent ein
**append-only Kosten-Ledger** in der Memory (`## Cost Ledger`-Tabelle).

- **Am Ende jedes Laufs** genau **eine Zeile** anhängen: Datum (JJJJ-MM-TT),
  genutzte Modelle, Token rein, Token raus, Kosten in `$` (Summe aus Haiku-
  Klassifikation + Hauptmodell, mit den zur Laufzeit aktuellen Modellpreisen).
- **Vor dem Schreiben des Footers** die bestehende Tabelle lesen und summieren:
  *„Diesen Monat"* = Summe der Zeilen des laufenden Kalendermonats, *„Gesamt"* =
  Summe aller Zeilen. Dann diesen Lauf addieren und beide Werte im Footer zeigen.
- Ledger ist **rein additiv** — nie rückwirkend Zeilen ändern. Nur korrigieren,
  wenn ein Lauf nachweislich doppelt eingetragen wurde.

## Aktien-Tracker

Lief im AI-Digest eine Aktien-Analyse, wird **nach jedem Lauf** zusätzlich der
Aktien-Tracker (`memory/stock-tracker.md`, lokal/gitignored) fortgeschrieben —
analog zum Cost Ledger, append-only Signal-Log + neu berechneter Stand pro
Ticker. Format und Regeln stehen in `core/stock-analysis.md`.

## Pflege-Disziplin

- Am **Ende jedes Laufs** Memory aktualisieren: neue Lern-Einträge **und** eine
  neue Zeile im Cost Ledger (sowie der Aktien-Tracker, falls Aktien-Analyse lief).
- Memory **am Anfang jedes Laufs lesen**, bevor klassifiziert wird (Lernlog
  *und* Cost Ledger — letzteres für die kumulierten Werte im Footer).
- Lernlog ist additiv; veraltete/widersprüchliche Einträge korrigieren statt
  doppeln.
- Memory enthält **keine Passwörter** und keine sensiblen Mailinhalte — nur
  Sortier-/Stil-Wissen.
