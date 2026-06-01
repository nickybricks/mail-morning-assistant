#!/usr/bin/env python3
"""Wendet Klassifikations-Entscheidungen auf das Gmail-Postfach an (Labeln +
konservatives Archivieren) — über die Gmail-REST-API per HTTPS, cloud-tauglich.

Eingabe: eine JSON-Datei mit den Entscheidungen des Modells. Das Modell entscheidet
nur Heim-Ordner + ob Aktion nötig; die INBOX-/Archiv-Logik steckt HIER (eine Stelle):

    {"actions": [
        {"id": "<gmail-message-id>", "label": "Maily/Geld/Purchases", "now": false},
        {"id": "<gmail-message-id>", "label": "Maily/Arbeit/MAVEKO",   "now": true},
        {"id": "<gmail-message-id>", "label": "Maily/Unklar",          "now": false}
    ]}

Regeln (konservativ, weil unbeaufsichtigt):
- Jede Mail bekommt GENAU EIN Heim-Label (muss mit "<assistant_name>/" beginnen).
- `now: true`  -> zusätzlich <Name>/!Now, Mail BLEIBT in der INBOX (nicht archiviert).
- Label == <Name>/Unklar -> Mail bleibt in der INBOX (Fallback, Nutzer sieht sie).
- sonst -> Mail wird archiviert (Label INBOX entfernt).

Sicherheits-Guards (hart, nicht umgehbar):
- Es werden NUR Labels mit dem Assistenten-Präfix gesetzt (resolve, create=False) —
  fremde/System-Labels (SPAM, TRASH, CATEGORY_*, …) werden abgelehnt.
- Das EINZIGE Label, das je entfernt wird, ist INBOX. Nie löschen, nie in Spam/Trash.
- Existiert ein Label nicht, wird die Aktion übersprungen (kein Anlegen neuer Ordner
  im unbeaufsichtigten Lauf) und im Ergebnis gemeldet.

    python3 apply_actions.py <actions.json> [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _gmail_common import load_config, access_token, api, resolve_label, die  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("actions")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    name = cfg.get("assistant_name") or "Mail"
    prefix = f"{name}/"
    now_label_name = f"{name}/!Now"

    data = json.loads(Path(args.actions).read_text(encoding="utf-8"))
    actions = data.get("actions", data) if isinstance(data, dict) else data
    if not isinstance(actions, list):
        die("actions-Datei: erwarte {\"actions\": [...]} oder eine Liste.")

    token = access_token(cfg["email"])

    # Label-Namen -> IDs einmal auflösen (Cache), inkl. !Now.
    label_cache = {}

    def label_id(label_name):
        if label_name not in label_cache:
            label_cache[label_name] = resolve_label(token, label_name, create=False)
        return label_cache[label_name]

    now_id = label_id(now_label_name)

    result = {"dry_run": args.dry_run, "applied": 0, "skipped": [], "errors": []}

    for act in actions:
        mid = act.get("id")
        label = (act.get("label") or "").strip()
        needs_now = bool(act.get("now"))

        if not mid or not label:
            result["skipped"].append({"id": mid, "reason": "id oder label fehlt"})
            continue
        # Guard: nur eigene Labels.
        if not label.startswith(prefix):
            result["skipped"].append({"id": mid, "label": label,
                                      "reason": f"Label ohne Präfix '{prefix}' — abgelehnt"})
            continue
        lid = label_id(label)
        if not lid:
            result["skipped"].append({"id": mid, "label": label,
                                      "reason": "Label existiert nicht (kein Anlegen im Auto-Lauf)"})
            continue

        is_unklar = label == f"{name}/Unklar"
        add = [lid]
        remove = []
        if needs_now and not is_unklar:
            if now_id:
                add.append(now_id)
            keep_inbox = True
        elif is_unklar:
            keep_inbox = True
        else:
            keep_inbox = False
        if not keep_inbox:
            remove = ["INBOX"]

        if args.dry_run:
            result["applied"] += 1
            result.setdefault("plan", []).append(
                {"id": mid, "add": add, "remove": remove, "label": label})
            continue
        try:
            api("POST", f"/messages/{mid}/modify", token,
                body={"addLabelIds": add, "removeLabelIds": remove})
            result["applied"] += 1
        except SystemExit as e:
            result["errors"].append({"id": mid, "label": label, "error": str(e)})

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
