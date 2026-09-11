# Nicks Präferenzen — verbindliches Regelbuch für Maily

> Diese Datei ist **versioniert** und wird bei **jedem** Lauf gelesen.
> Sie wächst mit: Nach jedem Lauf sagt Nick im Chat, was besser laufen soll —
> die Regel kommt hier rein, wird committet und gilt ab dem nächsten Lauf.
> Alles andere in `memory/` ist lokal und überlebt keinen Cloud-Lauf.

---

## Entwürfe

### Sie vs. Du — Förmlichkeit spiegeln
Maily spiegelt die Anrede des Absenders, statt pauschal zu duzen.

- Schreibt jemand auf Deutsch mit **„Sie"** → Antwort ebenfalls mit **„Sie"**.
  Anrede „Sehr geehrte/r Frau/Herr {Nachname}," · Gruß „Mit freundlichen Grüßen" + „Nick Algner".
- Schreibt jemand auf Deutsch mit **„Du"** → informell wie bisher.
  Anrede „Hey {Vorname}," / „Hallo {Name}," · Gruß „Liebe Grüße" + „Nick".
- **Englisch** → wie bisher: „Hey {Vorname}," / „Hi {Name}," / „Hello," · „Best," + „Nick".

Gilt für **alle** Absender, nicht nur bekannte Personen. Im Zweifel die
Förmlichkeit der Eingangsmail übernehmen.

Unverändert gültig: nie „LG" abkürzen, immer „Liebe Grüße" ausschreiben.
Signatur immer ans Ende.

---

## Briefings

### Alte Briefings aus dem Posteingang räumen
Damit sich keine Briefings stapeln, räumt Maily am **Ende jedes Laufs** auf.

1. Suchen: `from:nick@algner.de in:inbox subject:"Maily-Briefing"`
   (gelesen **und** ungelesen — alles, was noch in der INBOX liegt).
2. Nach Datum sortieren. Das **neueste** Briefing (das gerade zugestellte)
   bleibt im Posteingang.
3. Alle **älteren**: Ist eines davon noch **ungelesen**, dessen offene
   🔴-Punkte kurz prüfen und als Abschnitt
   „📬 Aus dem letzten Briefing (ungelesen)" oben ins neue Briefing übernehmen —
   damit nichts untergeht, was Nick noch nicht gesehen hat.
4. Dann alle älteren archivieren: nur das `INBOX`-Label entfernen.
   Sie bleiben unter `Maily/Briefings` auffindbar. **Nichts löschen.**

**AI-Digests nicht anfassen.** Die bleiben unberührt im Posteingang liegen.

Getestet und bestätigt am 09.09.2026.

---

## Lernen: Maily schlägt vor, Nick entscheidet

Maily schreibt sich **niemals selbst** Regeln. Ein automatischer Lauf committet
nicht — er hat keinen Menschen, der gegenliest, und eine falsch gezogene Regel
würde ab dann bei jedem Lauf gelten.

Stattdessen **schlägt** Maily Regeln vor, im Briefing unter „💡 Vorschläge"
(Format siehe `core/briefing.md`). Nick sagt im Chat ja oder nein:

- **Ja** → die Regel kommt in diese Datei, wird committet und gilt ab dem
  nächsten Lauf. Zeile ins Änderungsprotokoll.
- **Nein** → Zeile unter „Abgelehnte Vorschläge". **Nicht erneut vorschlagen.**

### Wann ein Vorschlag sinnvoll ist
Nur bei echtem, wiederkehrendem Signal aus **diesem** Lauf — nicht bei
Einzelfällen, nicht als Pflichtübung:

- Mehrere Mails desselben Absenders landen in `Unklar`.
- Ein Absender passt erkennbar schlecht in sein Label (z. B. ein Newsletter, den
  Nick liest, unter `Werbung`).
- Eine Mehrdeutigkeits-Regel greift wiederholt nicht sauber
  (z. B. ImmoScout Gewerbe vs. Wohnung).
- Ein `!Now` ohne Entwurf, bei dem eine Antwort offensichtlich nötig gewesen wäre
  — oder umgekehrt ein überflüssiger Entwurf.

**Maximal 3 Vorschläge pro Lauf.** Gibt es nichts, entfällt der Abschnitt
komplett — kein „heute nichts". Ein Block, der jeden Tag erscheint, wird
überlesen.

### Abgelehnte Vorschläge (nicht erneut vorschlagen)

_(noch keine)_

---

## Änderungsprotokoll

| Datum | Regel | Anlass |
|-------|-------|--------|
| 2026-09-09 | Sie/Du spiegeln statt pauschal duzen | Ein Entwurf an einen förmlichen Absender wurde fälschlich geduzt |
| 2026-09-09 | Alte Briefings archivieren, AI-Digest ausgenommen | Briefings vom 07. und 08.09. stapelten sich im Posteingang |
