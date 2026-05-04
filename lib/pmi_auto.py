"""
Buena Piloto — PMI Auto-Plan Generator
Passt den Base-PMI-Plan basierend auf DD-Findings an:
- Fügt Tasks hinzu wenn Risiken es erfordern (z.B. Excel/Word → Datenrekonstruktion)
- Verschiebt Timing wenn Risiken hoch sind (z.B. key_person_risk → Day 1-7)
- Überschreibt Owner-Empfehlungen kontextspezifisch
- Markiert Auto-Tasks transparent
"""
from copy import deepcopy
from typing import Any


# ──────────────────────────────────────────────────────────────────────────
# Auto-Plan Regeln
# ──────────────────────────────────────────────────────────────────────────
# Jede Regel: (condition_fn, modifications)
# modifications: dict mit
#   - "add_tasks": [{workstream_id, task_data}]
#   - "modify_tasks": [{task_id, changes}]
#   - "trigger_text": str (zeigt warum die Regel angewandt wurde)


def _excel_word_software(target: dict) -> bool:
    return target.get("operations", {}).get("primary_software") == "Excel/Word"


def _on_prem_deployment(target: dict) -> bool:
    return target.get("operations", {}).get("deployment") == "On-Prem"


def _key_person_risk(target: dict) -> bool:
    return bool(target.get("people", {}).get("key_person_risk"))


def _high_customer_concentration(target: dict) -> bool:
    return (target.get("customers", {}).get("top3_pct", 0) or 0) > 35


def _short_transition(target: dict) -> bool:
    return target.get("company_basics", {}).get("transition_period") == "<3 Monate"


def _aging_workforce(target: dict) -> bool:
    pp = target.get("people", {}) or {}
    over_60 = pp.get("employees_over_60", 0) or 0
    fte_total = (
        (pp.get("fte_property_manager", 0) or 0)
        + (pp.get("fte_accounting", 0) or 0)
        + (pp.get("fte_other", 0) or 0)
    )
    return fte_total > 0 and (over_60 / fte_total) > 0.30


def _complex_ownership(target: dict) -> bool:
    cb = target.get("company_basics", {}) or {}
    return (cb.get("shareholders", 1) or 1) > 4 or (
        cb.get("shareholders", 1) > 1 and not cb.get("majority_shareholder", True)
    )


# Rule-Definitionen
AUTO_RULES = [
    {
        "id": "excel_software_recon",
        "condition": _excel_word_software,
        "trigger_text": "DD-Flag: Tech-Stack ist Excel/Word — Datenrekonstruktion + Custom-Mapping nötig",
        "add_tasks": [
            {
                "workstream_id": "ws1",
                "after_task_id": "1.1",
                "task": {
                    "id": "1.1.A",
                    "name": "Excel-/Word-Datenrekonstruktion",
                    "default_owner": "Buena Tech",
                    "timing_days_after_close": "1-21",
                    "dependencies": "1.1",
                    "acceptance_criteria": "Alle Verträge, Eigentümer, Konten aus Excel/Word in strukturiertes Schema überführt; Diskrepanzen mit Source-Files quantifiziert.",
                    "notes": "Hochkritisch: ohne Strukturierung keine Migration möglich. Plane mind. 2 FTE für 3 Wochen.",
                },
            },
            {
                "workstream_id": "ws1",
                "after_task_id": "1.5",
                "task": {
                    "id": "1.5.A",
                    "name": "Erweiterte Parallelbetrieb-Phase (90 Tage statt 25)",
                    "default_owner": "PMI Lead",
                    "timing_days_after_close": "35-125",
                    "dependencies": "1.4 + 1.1.A",
                    "acceptance_criteria": "Verlängerter Parallelbetrieb um Datenfehler aus Excel-Quellen aufzudecken bevor Cut-Over.",
                    "notes": "Bei Excel/Word-Quellen sind Edge-Cases häufig — länger parallel laufen, weniger Risiko.",
                },
            },
        ],
    },
    {
        "id": "on_prem_physical_access",
        "condition": _on_prem_deployment,
        "trigger_text": "DD-Flag: On-Prem Deployment — physischer Server-Zugang erforderlich",
        "add_tasks": [
            {
                "workstream_id": "ws1",
                "after_task_id": "1.1",
                "task": {
                    "id": "1.1.B",
                    "name": "Physischer Server-Zugang & Backup",
                    "default_owner": "Buena Tech + lokaler Geschäftsführer",
                    "timing_days_after_close": "1-3",
                    "dependencies": "Closing",
                    "acceptance_criteria": "VPN-Zugang oder physische Anwesenheit am Server-Standort; Voll-Backup vor jeglicher Änderung.",
                    "notes": "On-Prem Server haben oft kein dokumentiertes Backup. Erst sichern, dann anfassen.",
                },
            },
        ],
        "modify_tasks": [],
    },
    {
        "id": "key_person_urgent_binding",
        "condition": _key_person_risk,
        "trigger_text": "DD-Flag: Schlüsselperson-Risiko identifiziert — Bindung priorisiert",
        "modify_tasks": [
            {
                "task_id": "2.5",
                "changes": {
                    "timing_days_after_close": "1-7",
                    "notes": "AUTO-PRIORISIERT: Schlüsselperson laut DD identifiziert → Bindung MUSS innerhalb 7 Tagen unter Dach und Fach sein, sonst Existenz-Risiko.",
                },
            },
        ],
        "add_tasks": [
            {
                "workstream_id": "ws2",
                "after_task_id": "2.5",
                "task": {
                    "id": "2.5.A",
                    "name": "Earn-Out / Retention-Bonus für Schlüsselperson(en)",
                    "default_owner": "VP Property Management",
                    "timing_days_after_close": "1-14",
                    "dependencies": "2.5",
                    "acceptance_criteria": "Retention-Vertrag mit 2-3J Laufzeit unterschrieben; Vesting an Performance-KPIs gekoppelt.",
                    "notes": "Standard-Anteil: 10-20% Bonus über Marktgehalt, gestaffelt über 24 Monate.",
                },
            },
        ],
    },
    {
        "id": "high_concentration_top_customer",
        "condition": _high_customer_concentration,
        "trigger_text": "DD-Flag: Top-3 Customer-Konzentration > 35% — Frontload Customer-Tour",
        "modify_tasks": [
            {
                "task_id": "3.3",
                "changes": {
                    "timing_days_after_close": "1-14",
                    "notes": "AUTO-PRIORISIERT: Hohe Customer-Konzentration → Top-3 müssen sofort betreut werden, sonst Vertragsverlust = Bewertungs-Schock.",
                },
            },
        ],
        "add_tasks": [
            {
                "workstream_id": "ws3",
                "after_task_id": "3.3",
                "task": {
                    "id": "3.3.A",
                    "name": "Vertragsverlängerung Top-3-Kunden initiieren",
                    "default_owner": "PMI Lead + VP",
                    "timing_days_after_close": "14-60",
                    "dependencies": "3.3",
                    "acceptance_criteria": "Mindestens 2 von 3 Top-Kunden haben Vertragsverlängerung mit 3-5J Laufzeit unterschrieben.",
                    "notes": "Auch wenn Verträge noch lange laufen — proaktive Verlängerung signalisiert Stabilität und reduziert Bewertungs-Risiko bei Exit.",
                },
            },
        ],
    },
    {
        "id": "short_transition_sprint",
        "condition": _short_transition,
        "trigger_text": "DD-Flag: Übergangsperiode < 3 Monate — Knowledge-Transfer-Sprint nötig",
        "modify_tasks": [
            {
                "task_id": "2.1",
                "changes": {
                    "timing_days_after_close": "1",
                    "notes": "AUTO-VERDICHTET: Aufgrund kurzer Übergangsphase All-Hands sofort, nicht erst Day 1.",
                },
            },
            {
                "task_id": "2.2",
                "changes": {
                    "timing_days_after_close": "1-10",
                    "notes": "AUTO-VERDICHTET: 1:1 Interviews innerhalb 10 Tagen statt 21 — Knowledge-Transfer-Sprint.",
                },
            },
        ],
        "add_tasks": [
            {
                "workstream_id": "ws2",
                "after_task_id": "2.2",
                "task": {
                    "id": "2.2.A",
                    "name": "Knowledge-Transfer-Sprint (Schattieren ehemaliger Inhaber)",
                    "default_owner": "PMI Lead + lokaler Geschäftsführer",
                    "timing_days_after_close": "1-30",
                    "dependencies": "2.2",
                    "acceptance_criteria": "Tägliches Schattieren des Verkäufers durch Buena-Mitarbeiter; alle Top-Eigentümer-Beziehungen dokumentiert.",
                    "notes": "Bei <3 Monate Übergang: jede Stunde mit dem Verkäufer ist Gold wert.",
                },
            },
        ],
    },
    {
        "id": "aging_workforce_succession",
        "condition": _aging_workforce,
        "trigger_text": "DD-Flag: > 30% Mitarbeiter > 60 Jahre — Wissens-Transfer-Programm",
        "add_tasks": [
            {
                "workstream_id": "ws2",
                "after_task_id": "2.6",
                "task": {
                    "id": "2.6.A",
                    "name": "Wissens-Transfer-Programm für ältere Mitarbeiter",
                    "default_owner": "Buena People Team + lokaler Geschäftsführer",
                    "timing_days_after_close": "30-180",
                    "dependencies": "2.2",
                    "acceptance_criteria": "Strukturiertes Mentoring-Programm: jüngere MA werden ältere Kollegen schattieren; Prozess-Dokumentation pro Eigentümer.",
                    "notes": "Pensions-Welle vorhersehbar — JETZT dokumentieren, nicht erst wenn die Leute weg sind.",
                },
            },
        ],
    },
    {
        "id": "complex_ownership_extended_negotiation",
        "condition": _complex_ownership,
        "trigger_text": "DD-Flag: Komplexe Eigentümerstruktur — verlängerte Verhandlungs-Vorlauf",
        "add_tasks": [
            {
                "workstream_id": "ws3",
                "after_task_id": "3.2",
                "task": {
                    "id": "3.2.A",
                    "name": "WEG-Beirats-Konsens herstellen (komplexe Eigentümer)",
                    "default_owner": "PMI Lead + lokaler Verwalter",
                    "timing_days_after_close": "7-45",
                    "dependencies": "3.2",
                    "acceptance_criteria": "Schriftliche Zustimmung aller WEG-Beiräte zur Verwaltungsfortführung; bei Verweigerung: Mediations-Plan.",
                    "notes": "Bei mehrköpfigen Eigentümer-Strukturen ist Beirats-Konsens essentiell — eine einzige Verweigerung kann Verwaltungswechsel-Domino auslösen.",
                },
            },
        ],
    },
]


# ──────────────────────────────────────────────────────────────────────────
# Generator
# ──────────────────────────────────────────────────────────────────────────
def generate_auto_plan(base_template: dict, target: dict) -> dict:
    """
    Adaptiert den Base-PMI-Plan basierend auf Target-Daten.

    Returns:
        {
            "workstreams": [...] (mit auto-generated tasks markiert),
            "owner_options": [...],
            "applied_rules": [
                {"rule_id", "trigger_text", "tasks_added", "tasks_modified"}
            ]
        }
    """
    plan = deepcopy(base_template)
    applied_rules = []

    for rule in AUTO_RULES:
        if not rule["condition"](target):
            continue

        rule_summary = {
            "rule_id": rule["id"],
            "trigger_text": rule["trigger_text"],
            "tasks_added": [],
            "tasks_modified": [],
        }

        # Apply modifications
        for mod in rule.get("modify_tasks", []):
            target_task_id = mod["task_id"]
            for ws in plan["workstreams"]:
                for task in ws["tasks"]:
                    if task["id"] == target_task_id:
                        task["auto_modified"] = True
                        task["auto_modified_by"] = rule["id"]
                        # Apply changes
                        for k, v in mod["changes"].items():
                            task[k] = v
                        rule_summary["tasks_modified"].append(target_task_id)

        # Apply additions
        for add in rule.get("add_tasks", []):
            ws_id = add["workstream_id"]
            after_id = add["after_task_id"]
            new_task = dict(add["task"])
            new_task["auto_generated"] = True
            new_task["auto_generated_by"] = rule["id"]

            # Find target workstream and insert after the specified task
            for ws in plan["workstreams"]:
                if ws["id"] != ws_id:
                    continue
                # Find insert position
                insert_idx = len(ws["tasks"])
                for i, t in enumerate(ws["tasks"]):
                    if t["id"] == after_id:
                        insert_idx = i + 1
                        break
                ws["tasks"].insert(insert_idx, new_task)
                rule_summary["tasks_added"].append(new_task["id"])

        applied_rules.append(rule_summary)

    plan["applied_rules"] = applied_rules
    plan["auto_plan_active"] = len(applied_rules) > 0
    return plan


def count_auto_tasks(plan: dict) -> dict:
    """Zählt wie viele Tasks pro Workstream auto-generated/modified sind."""
    counts = {}
    for ws in plan["workstreams"]:
        added = sum(1 for t in ws["tasks"] if t.get("auto_generated"))
        modified = sum(1 for t in ws["tasks"] if t.get("auto_modified"))
        counts[ws["id"]] = {"added": added, "modified": modified, "total": len(ws["tasks"])}
    return counts
