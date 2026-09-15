# AI-Digest — Einstellungen, Workflow & Präferenzen

Diese Datei ist die **einzige Quelle der Wahrheit** für den automatischen
AI-Digest-Lauf. Der Scheduled-Prompt liest sie als erstes. Feedback und
Lerneffekte werden hier festgehalten — nie im Prompt selbst.

---

## 1. Config (config.json)

Beim Start des Laufs diese `config.json` ins Wurzelverzeichnis schreiben:

```json
{
  "provider": "gmail-rest",
  "assistant_name": "Maily",
  "email": "nick@algner.de",
  "ai_digest_senders": [
    "alphasignal.ai",
    "swyx+ainews@substack.com",
    "techpresso@dupple.com",
    "lennysnewsletter.com",
    "t3n.de",
    "synthszr.com"
  ],
  "ai_digest_window_hours": 24,
  "ai_digest_label": "Maily/AI-Digest"
}
```

OAuth-Secrets stehen in ENV `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` /
`GMAIL_REFRESH_TOKEN`. Fehlt eine → Lauf abbrechen und im Log melden.

---

## 2. Workflow-Ablauf (Schritt für Schritt)

**EISERN:** nichts senden außer dieser einen Mail (`messages.insert` legt nur ab),
nichts löschen, kein Spam/Papierkorb, keine Drafts, Quell-Newsletter NICHT
verschieben/archivieren (bleiben in der Inbox).

### Schritt A — Ungelesene alte Digests holen
```bash
python3 adapters/gmail-rest/fetch_prev_digests.py --unread-inbox > unread_digests.json
```
- `count > 0`: Inhalt später vollständig in den neuen Digest einarbeiten.
- Im Digest-Header „N Ausgaben über Nacht" um „+ Nachhol-Digest vom TT.MM." ergänzen.

### Schritt B — Neue Newsletter-Inhalte holen
```bash
python3 adapters/gmail-rest/fetch_digest.py > digest_in.json
```
- `body_excerpt` enthält Original-Links als `[text](url)` und Bilder als `![alt](url)`.
- Sind **0 neue Ausgaben** UND `unread_digests.json` ebenfalls leer → **keine Mail
  erzeugen**, sauber beenden.

### Schritt C — Digest-HTML schreiben (`digest.html`)
Lies `core/briefing.md`, Abschnitt „🤖 AI-Digest" für das genaue Schema.
Kurzform:
- Oben 2–3 Sätze Tages-Zusammenfassung.
- Feste Abschnitte: 🚀 Releases & Modelle / 🛠️ Tools & Produkte /
  📚 Lesestoff & Essays / ⚡ Kurz notiert.
- Inhalte aus ungelesenen alten Digests (Schritt A) vollständig einarbeiten.
- Bullet Points `<ul><li>`, ausführlich (1–3+ Sätze), Quellen als
  `<a href="url">…</a>`, aussagekräftige Bilder als
  `<img src="url" style="max-width:100%;height:auto">` (keine Logos/Spacer/Tracking).
- Themen über mehrere Newsletter zusammenführen (kein Doppeln).
- Leerer Abschnitt → „— heute nichts".
- Nur inneres HTML-Fragment (kein `<html>`/`<body>`/`<style>`-Block).
- Nur was in den Newslettern steht, nichts erfinden.
- Entdopplung: was in bereits **gelesenen** alten Digests stand, weglassen
  (außer echter neuer Stand).

### Schritt D — Zustellen
```bash
python3 adapters/gmail-rest/deliver_briefing.py digest.html --html \
  --folder "Maily/AI-Digest" \
  --subject "🤖 AI-Digest — $(date +%d.%m.%Y)" \
  --also-inbox
```

### Schritt E — Alte ungelesene Digests archivieren
```bash
python3 adapters/gmail-rest/archive_old_digests.py unread_digests.json
```
Nur ausführen wenn `unread_digests.json` → `count > 0`.
Entfernt INBOX-Label; Mails bleiben im `Maily/AI-Digest`-Label.

### Schritt F — Log
Ausgabe: Anzahl neuer Ausgaben + Anzahl archivierter alter Digests + ob Zustellung ok.

---

## 3. Präferenzen & Lernlog

Hier werden Feedback und Lerneffekte festgehalten. Neueste Einträge oben.

### Schreibstil
- Deutsch, direkt, kein Marketingsprech.
- Bullets ausführlich — Leser soll Thema vollständig verstehen ohne Original zu öffnen.
- Konkrete Zahlen, Namen und den „warum-relevant"-Punkt immer nennen.

### Quellen & Links
- Nur saubere Ziel-URLs verwenden (keine Tracking-/Weiterleitungs-Links).
- Pro Bullet max. 1–2 Links; nicht jedes Wort verlinken.
- Bilder nur einbetten wenn sie echten Inhalt zeigen (Chart, Screenshot, Produkt) —
  keine Logos, Avatare, Spacer.

### Sender-Eigenheiten
- **AlphaSignal:** Alle Links sind Tracking-Redirects → aus dem Text erschließbare
  Ziel-URLs verwenden (GitHub-Repos, wo explizit genannt; sonst Quelle nur als Text).
- **AINews (swyx):** Viele Substack-Redirects → Substack-Post-URL als Hauptlink nutzen.
- **Synthszr:** Liefert gute direkte URLs (TechCrunch, Bloomberg, The Verge etc.) →
  diese direkt verwenden.
- **Techpresso:** Tracking-Links über elink640.dupple.com → nur den Inhalt entnehmen,
  keinen Link setzen oder Zieldomain aus dem Linktext erschließen.

### Entdopplung über Tage
- Bereits gelesene Digests: Themen weglassen, es sei denn echter neuer Stand.
- Noch **ungelesene** Digests in der Inbox: vollständig einarbeiten (nicht weglassen).

---

*Letzte Aktualisierung: 2026-09-15*
