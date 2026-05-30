# Sender-Registry — {EMAIL}

Eine Zeile pro Absender/Domain. Der Assistent liest diese Datei vor jeder Triage als
zusätzliche Entscheidungshilfe (ergänzt den Lernlog, ersetzt ihn nicht).

**Format:** `<absender oder domain> | <kategorie> | <heim-ordner oder "—"> | <kurznotiz>`

Kategorien:
- `vip` — immer sichtbar lassen, nie wegsortieren, Entwurf ggf. priorisiert.
- `action` — meist Aktion nötig (z. B. Kunde, der schreibt) → oft `!Now`.
- `transactional` — wichtige automatische Mails (Rechnungen, Bestätigungen) — sichtbar lassen.
- `noise` — Newsletter/Werbung/Routine-Notifs — wegsortieren.

## Bekannte Absender

<!-- wird im ersten Live-Lauf und durch Korrekturen befüllt -->
