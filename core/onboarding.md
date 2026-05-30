# Onboarding — geführter Erststart

Ziel: Auch jemand **ohne Technik-Kenntnisse** richtet den Assistenten in wenigen
Minuten ein. Eine Frage (bzw. ein Thema) pro Schritt, Auswahl per Karten wo
möglich, offene Frage wo es persönlich wird. Immer erklären **warum** etwas
gebraucht wird, nie nur „gib X ein". Nach jedem Schritt das Ergebnis kurz
bestätigen.

Begrüßung zuerst, warm und knapp (Name ist noch nicht vergeben — generisch
bleiben):
> „Hi! Ich werde dein persönlicher Mail-Assistent — ich sortiere morgens deine
> Mails, schreibe dir ein kurzes Briefing und bereite Antwort-Entwürfe vor.
> Senden tust immer du selbst. Lass uns kurz einrichten — dauert ein paar Minuten."

---

## Schritt 0 — Wie soll ich heißen?

Offene Frage, als Allererstes:
> „Zuerst: Wie möchtest du mich nennen? Such mir einen Namen aus — z. B. ‚Maily',
> ‚Postbote', ‚Inbox', irgendwas. So nenne ich mich ab jetzt, und deine
> Mail-Ordner bekommen diesen Namen als Etikett."

- Antwort als `assistant_name` in `config.json` speichern.
- **Ab hier sich selbst immer mit diesem Namen benennen.**
- Der Name wird auch zum **Präfix der Themen-Ordner/Labels** (Schritt 4):
  `<assistant_name>/Finanzen`, `<assistant_name>/!Now`, …
- Kein Zwang zu einem Default — wählt der Nutzer nichts, freundlich einen
  Vorschlag machen (z. B. „Maily") und bestätigen lassen.

---

## Schritt 1 — Anbieter wählen

Frage (als Karten): **„Wo liegt dein Postfach?"**

| Karte | Bedeutung | Adapter |
|---|---|---|
| **Gmail / Google Workspace** | gmail.com oder eigene Domain bei Google | `gmail` |
| **all-inkl, IONOS/1&1, web.de, GMX, Strato …** | klassisches Postfach (IMAP) | `imap` |
| **Outlook / Microsoft 365** | outlook.com, Office-365-Postfach | `microsoft` |
| **Apple iCloud / Apple Mail** | icloud.com oder lokales Apple Mail | `apple-mail` |
| **Weiß ich nicht** | beim Erkennen helfen | — |

Bei „Weiß ich nicht": nach der E-Mail-Adresse fragen und an der Domain erkennen
(gmail.com→Gmail, outlook/hotmail/live→Microsoft, icloud/me/mac→Apple,
gmx/web.de/kasserver/ionos/strato→IMAP). Im Zweifel IMAP, das geht fast überall.

Gewählten Provider in `config.json` als `"provider"` festhalten und ab hier den
**provider-spezifischen Setup-Teil** des jeweiligen Adapters ausführen
(`adapters/<provider>/adapter.md`, Abschnitt „Onboarding"). Für IMAP siehe die
Provider-Presets dort — **nicht** nach kryptischen Hostnamen fragen, sondern die
bekannten Anbieter zur Auswahl bieten und Host/Port selbst füllen.

Verbindung sofort testen (Adapter holt probehalber die letzten Mails). Erst bei
Erfolg weiter. Bei Fehler: in einfachen Worten sagen was schiefging (falsches
Passwort? App-Passwort statt normalem nötig?) und den Schritt wiederholen.

---

## Schritt 2 — Wer bist du?

Offene Fragen, eine nach der anderen, warm:

- **Vorname** (für die Anrede im Briefing).
- **Sprache**, in der der Assistent mit dir spricht und Entwürfe schreibt
  (Default: Deutsch; bei internationalen Empfängern passt er die Entwurfssprache
  an den Empfänger an).
- **Was machst du** (1 Satz reicht — z. B. „Freelancer Webdesign", „Studentin",
  „Vertrieb bei einer Software-Firma")? Das hilft beim Sortieren und beim Ton.

Antworten in `memory/email-assistant-memory.md` (Abschnitt „User Profile")
festhalten.

---

## Schritt 3 — Schreibstil lernen

Der Assistent soll klingen wie der Nutzer, nicht wie ein Bot. Zwei Wege anbieten
(Karten):

| Karte | Vorgehen |
|---|---|
| **Aus meinen gesendeten Mails lernen (empfohlen)** | Adapter holt ~20–30 Mails aus „Gesendet". Anrede, Grußformel, Signatur, Ton, Sprache extrahieren → `voice/samples.md` mit 3–5 echten Beispielen schreiben. |
| **Ich beschreibe meinen Stil selbst** | Nachfragen: Du oder Sie? Locker oder formell? Standard-Grußformel? Signatur? → `voice/samples.md` aus den Antworten schreiben. |

In beiden Fällen `voice/samples.md` aus `voice/samples.template.md` ableiten.
Ergebnis dem Nutzer **zeigen** und absegnen lassen („Klingt das nach dir?"). Bei
Korrekturen anpassen. Niemals einen erfundenen Stil unterstellen.

---

## Schritt 4 — Themen-Ordner ableiten

**Datengetrieben** Ordner vorschlagen, statt eine Standardliste aufzuzwingen.
Alle Ordner/Labels tragen den in Schritt 0 gewählten **`assistant_name` als
Präfix**.

1. Adapter holt einen größeren Sender-Querschnitt (**90-Tage-Fenster**, ~100 Mails).
2. Per Haiku nach Themen clustern (Sender + Subject) → 6–10 Heim-Ordner plus den
   Status `!Now`, den Fallback `Unklar` und `Briefings`.
   - Dabei **Newsletter/Lesestoff berücksichtigen**: Bekommt der Nutzer regelmäßig
     abonnierte Newsletter, einen Heim-Ordner dafür vorsehen (z. B. `Lesestoff`
     oder thematisch), **getrennt von `Werbung`** — damit Gelesenes sauber
     einsortiert und auffindbar ist und nicht als „Müll" behandelt wird
     (siehe `core/classification.md`).
3. Vorschlag als Liste zeigen: „Ich würde diese Ordner anlegen: `<Name>/Finanzen`,
   `<Name>/Reisen`, … Passt das? Was fehlt, was ist überflüssig?" Erst nach OK
   anlegen.
4. Anlegen über den Adapter (Gmail: Labels; IMAP: Ordner), jeweils mit Präfix
   `<assistant_name>/`. Namen/IDs in `memory/` festhalten. Bestehende ähnliche
   Ordner/Labels **übernehmen** statt doppelt anzulegen.

Details der selbstlernenden Logik: `core/classification.md`.

**Briefing-Gruppierung wählen** (kurz, als Karten) — wie soll das Morgen-Briefing
gegliedert sein? In `config.json` → `briefing_grouping` speichern:

| Karte | Bedeutung |
|---|---|
| **Nach Dringlichkeit** (Default) | Jetzt / Kann warten / Zur Kenntnis / Newsletter / Werbung. |
| **Nach Projekt/Thema** | Gruppiert nach deinen Heim-Ordnern (z. B. Kunden, Projekte). Gut für projektgetriebene Postfächer. |
| **Eigene Gliederung** | Du beschreibst, wie du's haben willst — wird in `memory/` festgehalten. |

Egal welches Schema: Aktion-Mails (`!Now`) stehen immer zuerst/markiert, jede Mail
kriegt einen Satz, Newsletter sind kein „Müll" (siehe `core/briefing.md`).

---

## Schritt 5 — Probelauf

Einen echten Lauf über die letzten 24h machen, aber **nur als Vorschau**: Briefing
zeigen, Sortier-/Flag-Plan zeigen, einen Beispiel-Entwurf zeigen — noch nichts
ausführen. Den Nutzer fragen, ob die Sortierung passt; Korrekturen in den Lernlog.
Erst auf ausdrückliches OK den scharfen Lauf (siehe SKILL.md, Schritt 5).

---

## Schritt 6 — Rhythmus

Fragen, wie der Nutzer den Assistenten nutzen will (Karten):

| Karte | Bedeutung |
|---|---|
| **Auf Zuruf** | Nutzer sagt „mach meine Mails", wann er will. |
| **Automatisch nach Plan** | Läuft selbstständig (auch bei ausgeschaltetem Rechner, via Cloud-Routine — siehe `core/automation.md`). |

Bei **„Automatisch nach Plan"** zusätzlich abfragen — der Nutzer ist frei:

- **Wie oft?** z. B. einmal morgens, stündlich, alle 2/3/4 Stunden.
- **An welchen Tagen?** täglich, nur Werktage, oder bestimmte Tage.

Daraus den Cron-Ausdruck bilden (lokale Zeit) **und** `lookback_hours` passend
setzen (= Abstand zwischen zwei Läufen; stündlich → 1, täglich → 24), damit sich
Mails nicht wiederholen. Beispiele in `core/automation.md`. Nichts Automatisches
ohne ausdrückliche Zustimmung einrichten.

Abschluss warm, mit dem gewählten Namen: „Fertig, {Vorname}. Sag einfach ‚mach
meine Mails', wenn's losgehen soll — ich bin {assistant_name}." Einrichtung in
`config.json` + `memory/` final speichern.

---

## Onboarding-Prinzipien (immer)

- **Eine Sache pro Schritt.** Nie fünf Fragen auf einmal.
- **Warum vor Wie.** Kurz sagen, wozu eine Angabe dient.
- **Zeigen, dann bestätigen.** Jedes Ergebnis (Name, Stil, Ordner, Plan) absegnen
  lassen.
- **Kein Tech-Jargon** gegenüber Nicht-Technikern. „App-Passwort" wird erklärt,
  nicht vorausgesetzt.
- **Sicherheit gilt ab Minute eins** (siehe SKILL.md, Eiserne Regeln).
