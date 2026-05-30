# Microsoft-Adapter — STUB (noch nicht implementiert)

Für Outlook.com / Microsoft 365. Geplant, aber noch nicht gebaut.

## Geplanter Ansatz

Zwei Wege, je nach Tenant:

1. **MS Graph API** (bevorzugt für Microsoft 365) — OAuth, Zugriff auf Mail,
   Ordner (`mailFolders`), Kategorien/Flags und Entwürfe. Mapping:
   - Heim-Ordner → Graph `mailFolders`
   - Status `!Now` → Flag (`flag.flagStatus = flagged`) oder Kategorie
   - Entwurf → `POST /me/messages` mit `isDraft`
2. **IMAP-Fallback** — viele Microsoft-Postfächer sprechen IMAP
   (`outlook.office365.com`, Port 993). Dann den `imap`-Adapter nutzen. Achtung:
   einige Tenants erzwingen OAuth/Modern Auth und blockieren Basic-Auth-IMAP →
   dort führt nur Graph zum Ziel.

## Bis dahin

Beim Onboarding den Nutzer fragen, ob sein Postfach IMAP erlaubt. Wenn ja →
`imap`-Adapter mit Host `outlook.office365.com`. Wenn nein → ehrlich sagen, dass
der native Microsoft-Adapter noch aussteht.

## Datenmodell-Mapping (Zielbild)

| Konzept | Microsoft (Graph) |
|---|---|
| Heim-Ordner | mailFolder |
| Status `!Now` | flagStatus = flagged |
| Entwurf | message mit isDraft=true |
