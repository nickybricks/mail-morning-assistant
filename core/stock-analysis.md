# Aktien-Impact-Analyse & Aktien-Tracker

Zusatz zum **AI-Digest** (siehe `core/briefing.md`, Abschnitt „🤖 AI-Digest"):
Zu jeder AI/Tech-Meldung im Digest schätzt der Assistent ein, **welche
börsennotierten Firmen betroffen sind** und **in welche Richtung** (positiv /
neutral / negativ). Über die Zeit läuft daraus ein **Aktien-Tracker** mit, der
nach jedem Digest-Lauf fortgeschrieben wird.

> **Das ist eine Einschätzung, keine Anlageberatung.** Es werden **keine
> Kurse, Kursziele oder erfundenen Zahlen** produziert — nur die *Richtung*
> einer Einschätzung, abgeleitet aus dem, was tatsächlich in der Meldung steht.
> Eiserne Regel bleibt: keine erfundenen Fakten (siehe `SKILL.md`).

Aktiv nur, wenn `config.json → stock_analysis_enabled` `true` ist **und** ein
AI-Digest erzeugt wird. Ohne AI-Digest (keine `ai_digest_senders` / keine
Ausgaben) entfällt auch die Aktien-Analyse.

---

## 1. Von der Meldung zur betroffenen Aktie

Der Kern: nicht nur die **offensichtliche** Firma nennen, sondern die **Kette
dahinter** mitdenken. Eine Meldung trifft meist mehrere börsennotierte Werte
über verschiedene Rollen:

- **Direkt** — die Firma, um die es geht (Apple erhöht Preise → **Apple/AAPL**).
- **Zulieferer / Hersteller** — wer das Produkt liefert oder fertigt (OpenAI
  bringt eigenen Chip, gefertigt bei Broadcom → **Broadcom/AVGO** profitiert als
  Auftragsfertiger).
- **Konkurrent** — wer dadurch unter Druck gerät (eigener OpenAI-Chip →
  **Nvidia/NVDA** leichter Gegenwind im Inferenz-Markt).
- **Kunde / Abnehmer** — wer das Produkt einsetzt und dadurch Vor-/Nachteile hat.
- **Plattform / Ökosystem** — Cloud-Anbieter, App-Stores, Index-Schwergewichte,
  die mitgezogen werden.

**Vorgehen pro Meldung:**
1. Direkt betroffene Firma identifizieren.
2. Fragen: *Wer liefert? Wer konkurriert? Wer kauft?* — und nur die nennen, bei
   denen die Verbindung **konkret aus der Meldung** ableitbar ist (kein
   Brainstorming entfernter Werte).
3. Pro genannter Firma: Ticker + Richtung + **ein** kurzer Begründungs-Halbsatz,
   der die Rolle benennt („als Auftragsfertiger", „Konkurrenzdruck", „Großkunde").

Lieber **2–3 gut begründete** Werte als eine lange Liste vager Verbindungen.

## 2. Nicht-börsennotierte Firmen (OpenAI, Anthropic, xAI, Databricks …)

Viele AI-Player sind **privat / nicht handelbar**. Dann:
- Firma trotzdem nennen, aber klar als `nicht börsennotiert` markieren.
- Den **nächsten handelbaren Proxy** angeben, falls sinnvoll und konkret
  (OpenAI → **Microsoft/MSFT** als Großinvestor/Plattform; Anthropic →
  **Amazon/AMZN**, **Alphabet/GOOGL** als Investoren). Proxy klar als Proxy
  kennzeichnen, nicht so tun, als sei es dieselbe Firma.
- Gibt es keinen sinnvollen Proxy: nur die Firma nennen, Richtung `➖`.

## 3. Richtung & Konfidenz

**Richtung** (für die handelnde Firma, mittelfristige Lesart der Meldung):
- `⬆️ positiv` — Rückenwind (neuer Großauftrag, starke Zahlen, Marktanteil,
  erfolgreicher Launch).
- `➖ neutral` — Information ohne klare Richtung, oder Effekt unklar/eingepreist.
- `⬇️ negativ` — Gegenwind (Konkurrenzdruck, Margendruck, Risiko, Klage,
  verlorener Kunde).

**Konfidenz** — wie direkt der Zusammenhang ist:
- `hoch` — explizit in der Meldung (Firma X liefert für Y, Zahlen genannt).
- `mittel` — plausible, branchenübliche Verbindung.
- `niedrig` — Vermutung; dann entweder weglassen oder klar als „spekulativ"
  kennzeichnen. Im Zweifel weglassen.

Konfidenz steuert v.a., **ob** ein Wert genannt wird — `niedrig` muss nicht in
jeden Bullet. Im sichtbaren Text reicht ein `(spekulativ)`-Zusatz bei niedriger
Konfidenz; `hoch`/`mittel` brauchen keine Markierung.

## 4. Watchlist-Hervorhebung (optional)

`config.json → stock_watchlist` ist eine Liste von Tickern, die den Nutzer
besonders interessieren (z. B. `["AAPL","AVGO","NVDA"]`). Verhalten:
- **Ist die Liste leer:** offene Entdeckung — jede konkret betroffene Aktie wird
  analysiert, nichts priorisiert.
- **Ist die Liste gefüllt:** weiterhin **alle** betroffenen Aktien analysieren
  (auch außerhalb der Liste — gerade unbekannte Zulieferer sind wertvoll), aber
  Watchlist-Treffer **hervorheben** (im Aktien-Radar oben, im HTML mit ⭐ /
  fett). Die Watchlist ist ein Filter für *Aufmerksamkeit*, kein Filter für
  *Abdeckung*.

---

## 5. Darstellung im Digest

Zwei Stellen (Details und HTML-Regeln in `core/briefing.md`):

**a) Pro Bullet** — direkt unter dem Inhalt eine kompakte Impact-Zeile:
```
📈 Broadcom (AVGO) ⬆️ positiv — Auftragsfertiger des Chips, neuer Großkunde.
   Nvidia (NVDA) ⬇️ leicht negativ — Konkurrenzdruck im Inferenz-Markt.
   OpenAI ➖ nicht börsennotiert (Proxy: Microsoft/MSFT neutral).
```
Hat ein Bullet **keinen** plausiblen Aktienbezug (z. B. reiner Essay), keine
Impact-Zeile erzwingen — weglassen ist besser als an den Haaren herbeiziehen.

**b) Aktien-Radar** — ein fester Abschnitt am **Ende** des Digests, der den Tag
**pro Ticker** verdichtet (Netto-Signal über alle Bullets), Watchlist-Treffer
zuerst:
```
📊 Aktien-Radar — {Datum}
 • ⭐ Apple (AAPL) ⬆️ — Preiserhöhung iPhone-Linie (1 Meldung).
 • Broadcom (AVGO) ⬆️ — OpenAI-Chip-Auftrag (1 Meldung).
 • Nvidia (NVDA) ⬇️ — Inferenz-Konkurrenz durch OpenAI-Chip (1 Meldung).
 ↳ Einschätzung, keine Anlageberatung.
```

---

## 6. Der Aktien-Tracker (`memory/stock-tracker.md`)

Ein **fortlaufender** Tracker, der nach **jedem** Digest-Lauf ergänzt wird —
analog zum Cost Ledger (siehe `core/learning-log.md`). Liegt unter `memory/`
(**lokal, gitignored**), weil er aus den Mails des Nutzers abgeleitet und
persönlich ist. Pfad über `config.json → stock_tracker_path` (Default
`memory/stock-tracker.md`).

Zweck: **Trends über Zeit** sichtbar machen („Broadcom diese Woche zum 3. Mal
positiv"), nicht nur Tagesschnappschüsse.

### Aufbau

```markdown
# Aktien-Tracker

## Aktueller Stand (pro Ticker)
| Ticker | Firma | Trend (letzte ~14 Tage) | Letztes Signal | Letzter Auslöser |
|--------|-------|-------------------------|----------------|------------------|
| AVGO   | Broadcom | ⬆️⬆️⬆️ (3 pos)        | 2026-06-28     | OpenAI-Chip-Auftrag |
| NVDA   | Nvidia   | ⬇️➖ (1 neg, 1 neutr) | 2026-06-28     | Inferenz-Konkurrenz |

## Signal-Log (append-only)
| Datum | Ticker | Richtung | Konfidenz | Auslöser | Quelle |
|-------|--------|----------|-----------|----------|--------|
| 2026-06-28 | AVGO | ⬆️ | hoch  | OpenAI-Chip bei Broadcom gefertigt | TechCrunch |
| 2026-06-28 | NVDA | ⬇️ | mittel | Konkurrenzdruck Inferenz-Chip      | TechCrunch |
| 2026-06-28 | AAPL | ⬆️ | hoch  | Preiserhöhung iPhone-Linie         | Techpresso |
```

### Pflege-Regeln
- **Signal-Log ist append-only** — pro Lauf für **jede** im Digest genannte
  Aktie genau eine Zeile anhängen. Nie rückwirkend ändern.
- **„Aktueller Stand"** wird pro Lauf **neu berechnet** aus den Signalen der
  letzten ~14 Tage (Fenster großzügig, nicht hart): Trend = Folge der Richtungen,
  Netto-Tendenz. Tabelle nach Aktivität sortieren, Watchlist-Ticker zuerst.
- **Keine Kurse/Beträge** im Tracker — nur Richtung, Konfidenz, Auslöser, Quelle.
- **Entdopplung:** Greift derselbe Auslöser über mehrere Newsletter, **eine**
  Signal-Zeile (Quellen kommagetrennt), nicht pro Newsletter eine.
- Tracker existiert nicht? Beim ersten Lauf mit Aktien-Analyse anlegen.

### Wann fortschreiben
Im Tagesablauf bei **Schritt 8 (Memory pflegen)** — gemeinsam mit Lernlog und
Cost Ledger (siehe `SKILL.md` und `core/learning-log.md`). Reihenfolge: erst
Digest schreiben/zustellen, dann Signale daraus in den Tracker übernehmen.

### Lokal vs. Cloud-Routine (wichtig)
Der **datei-basierte** Tracker (`memory/stock-tracker.md`) lebt im **lokalen/
interaktiven** Lauf, wo `memory/` über die Läufe hinweg bestehen bleibt. Die
**claude.ai-Cloud-Routine** klont das Repo jedes Mal frisch und hat **kein
dauerhaftes `memory/`** — dort wird **keine** Tracker-Datei geschrieben.
Tagesanalyse (Impact-Zeilen) und Aktien-Radar funktionieren dort trotzdem
(zustandslos); den **Trend über Tage** leitet der Cloud-Lauf aus den vorherigen
Digest-Mails ab (`fetch_prev_digests.py` holt sie zurück, der Aktien-Radar steht
darin). Siehe `core/automation.md`, Weg A2.
</content>
</invoke>
