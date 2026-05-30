# Klassifikation — selbstlernend, kein Regelwerk

Der Assistent sortiert jede Mail in **genau einen Heim-Ordner** und vergibt quer dazu
den Status `!Now`, wenn eine Aktion nötig ist. Die Zuordnung läuft **nicht über
feste Regex/Regeln**, sondern über ein Sprachmodell mit Kontext plus einen
mitwachsenden Lernlog.

## Modellwahl

- **Klassifikation läuft mit Haiku** (günstig, schnell) — es sind viele Mails
  und die Aufgabe ist simpel. Das teurere Hauptmodell nur für Briefing-Text und
  Entwürfe nutzen.
- Eingabe pro Mail: **Sender, Subject, Snippet/Body-Anfang, Empfänger-Adresse,
  Uhrzeit** — und der relevante Auszug aus dem Lernlog.
- **Subject muss immer einfließen**, nicht nur der Sender: dieselbe Domain kann
  Bestellbestätigung (→ Finanzen) oder Newsletter (→ Lesestoff) sein.

## Heim-Ordner

Die konkreten Ordner werden beim Onboarding **datengetrieben** abgeleitet
(`core/onboarding.md`, Schritt 4), nicht vorgegeben. Alle Ordner/Labels tragen
den **Assistenten-Namen als Präfix** (`<Name>/Finanzen`, `<Name>/!Now`, …; z. B.
`Maily/Finanzen`). Typisch 6–10 Themen plus:

- **`!Now`** — Status, kein Ordner. Liegt quer über allen Heim-Ordnern. Bedeutet
  „braucht eine Antwort/Entscheidung". Nach Erledigung entfernt der Nutzer (oder
  der Assistent nach erkannter Antwort) das Flag; die Mail bleibt im Heim-Ordner.
- **`Unklar`** — Fallback, wenn Haiku sich nicht sicher ist (`confidence: low`
  oder kein eindeutiger Heim-Ordner). Diese Mails bekommen das Label **und
  bleiben in der Inbox**, damit der Nutzer sie sieht und korrigiert.
- **`Briefings`** — Ablage für die eigenen Morgen-Briefings des Assistenten.

## Newsletter & Werbung — auch die werden einsortiert, nie „Müll"

Auch Newsletter und Werbung bekommen einen **Heim-Ordner** und werden nie
gelöscht oder als Abfall behandelt. Unterschieden wird (steuert auch die
Briefing-Gruppierung 📰 vs 🛒, siehe `core/briefing.md`):

- **Lesestoff** — bewusst abonnierte Newsletter/Inhalte, die der Nutzer liest →
  eigener Heim-Ordner (z. B. `<Name>/Lesestoff` oder thematisch wie `<Name>/AI News`).
  Bleiben erhalten, im Briefing mit kurzem Teaser.
- **Werbung** — reine Angebote/Promos → `<Name>/Werbung`. Im Briefing knapp.

Ob ein Sender „Lesestoff" oder „Werbung" ist, lernt der Lernlog aus den
Korrekturen des Nutzers (z. B. „verschiebt t3n nach Lesestoff").

## Ablauf je Lauf

1. Lernlog aus `memory/` laden (Sender/Pattern → gelernte Heimat).
2. Pro Mail Haiku fragen: `{ home_folder, needs_action (bool), confidence }`.
   Bei `confidence: low` → `Unklar`, in Inbox lassen.
3. Plan dem Nutzer zeigen (siehe SKILL.md Schritt 5), erst nach OK ausführen.

## Lernen aus Korrekturen

Verschiebt der Nutzer eine Mail manuell in einen anderen Ordner (oder korrigiert
im Vorschau-Schritt), hält der Assistent das **Sender+Subject-Pattern mit der
neuen Heimat** im Lernlog fest (`core/learning-log.md`). Beim nächsten Lauf bezieht
Haiku das mit ein — gleiche/ähnliche Mails landen direkt richtig. So passt sich
der Assistent an neue Sender und Betreffmuster an, **ohne dass jemand Regeln pflegt**.

Passt eine Mail in **keinen** bestehenden Ordner und häuft sich das Thema, fragt
der Assistent beim nächsten Lauf, ob ein neuer Ordner sinnvoll ist — statt sie still in
`Unklar` zu sammeln.

## Heim-Ordner vs. Status — die eine Regel

> Jede Mail hat **einen** Heim-Ordner (Thema). `!Now` ist ein **Zustand**, kein
> Ort. Niemals einen „Aktion"-Ordner anlegen.
