"""
Buena Piloto — Form Engine
Schema-getriebene Form-Logik:
- Conditional Logic (show_if Rules)
- Validation (required fields, sum checks)
- Flag-Auswertung aus Antworten
- Mapping Form-Answers → Target-Struktur
- Preliminary Heuristic Scoring (Tag 4: Volle Engine)
"""
from datetime import date
from typing import Any


# ──────────────────────────────────────────────────────────────────────────
# Mapping: Question-ID → Target-Struktur-Pfad
# ──────────────────────────────────────────────────────────────────────────
QUESTION_TO_TARGET_PATH: dict[str, tuple[str, ...]] = {
    # Top-level
    "1.1": ("name",),
    "1.2": ("location",),
    # Company Basics
    "1.3": ("company_basics", "founded"),
    "1.4": ("company_basics", "legal_form"),
    "1.5": ("company_basics", "fte_total"),
    "1.6": ("company_basics", "shareholders"),
    "1.7": ("company_basics", "majority_shareholder"),
    "1.8": ("company_basics", "owner_age"),
    "1.9": ("company_basics", "sale_motivation"),
    "1.10": ("company_basics", "transition_period"),
    # Portfolio
    "2.1": ("portfolio", "units_total"),
    "2.2": ("portfolio", "weg_pct"),
    "2.3": ("portfolio", "miet_pct"),
    "2.4": ("portfolio", "sondereig_pct"),
    "2.5": ("portfolio", "gewerbe_pct"),
    "2.6": ("portfolio", "gewerbe_avg_contract_years"),
    "2.7": ("portfolio", "indexed_rentals_pct"),
    "2.8": ("portfolio", "weg_count"),
    "2.9": ("portfolio", "geo_spread_km"),
    "2.10": ("portfolio", "main_location_concentration"),
    # Customers
    "3.1": ("customers", "active_contracts"),
    "3.2": ("customers", "top1_pct"),
    "3.3": ("customers", "top3_pct"),
    "3.4": ("customers", "avg_contract_years"),
    "3.5": ("customers", "cancellation_months"),
    "3.6": ("customers", "has_special_contracts"),
    "3.7": ("customers", "special_contracts_count"),
    "3.8": ("customers", "special_contracts_desc"),
    "3.9": ("customers", "nrr_12m"),
    "3.10a": ("customers", "contracts_lost_24m"),
    "3.10b": ("customers", "units_lost_24m"),
    "3.11": ("customers", "stickiness_pct"),
    "3.12": ("customers", "pricing_range"),
    "3.13a": ("customers", "last_price_increase_year"),
    "3.13b": ("customers", "last_price_increase_pct"),
    # Operations
    "4.1": ("operations", "primary_software"),
    "4.2": ("operations", "deployment"),
    "4.3": ("operations", "software_age_years"),
    "4.4": ("operations", "owner_portal"),
    "4.5": ("operations", "digital_owner_pct"),
    "4.6": ("operations", "banking_integration"),
    "4.7": ("operations", "accounting_internal"),
    "4.8": ("operations", "tool_count"),
    "4.9": ("operations", "it_documentation"),
    "4.10": ("operations", "weg_minutes_digital_pct"),
    "4.11": ("operations", "manual_workflows"),
    # People
    "5.1": ("people", "fte_property_manager"),
    "5.2": ("people", "fte_accounting"),
    "5.3": ("people", "fte_other"),
    "5.4": ("people", "avg_pm_salary"),
    "5.5": ("people", "personnel_cost_ratio"),
    "5.6": ("people", "turnover_12m_pct"),
    "5.7": ("people", "open_vacancies"),
    "5.8": ("people", "key_person_risk"),
    "5.9": ("people", "key_person_bound"),
    "5.10": ("people", "tariff_binding"),
    "5.11": ("people", "employees_over_60"),
    # Financials
    "6.1": ("financials", "revenue_y1"),
    "6.2": ("financials", "revenue_y2"),
    "6.3": ("financials", "revenue_y3"),
    "6.4": ("financials", "ebitda_y1"),
    "6.5": ("financials", "ebitda_y2"),
    "6.6": ("financials", "ebitda_y3"),
    "6.7": ("financials", "existing_debt"),
    "6.8": ("financials", "ar_over_90d"),
    "6.9": ("financials", "trustee_funds"),
    "6.10": ("knockouts", "trustee_loss"),
    "6.11": ("financials", "tax_proceedings"),
    # Knockouts
    "7.1": ("knockouts", "weg_proceedings"),
    "7.2": ("knockouts", "gf_recalled"),
    "7.3": ("knockouts", "insolvency"),
    "7.4": ("knockouts", "labor_lawsuits"),
    "7.5": ("knockouts", "trustee_loss"),
    "7.6": ("knockouts", "gdpr_violations"),
}


# ──────────────────────────────────────────────────────────────────────────
# Conditional Logic
# ──────────────────────────────────────────────────────────────────────────
def evaluate_condition(condition: dict, answers: dict) -> bool:
    """Wertet eine `show_if`-Bedingung gegen den aktuellen Antwort-State aus."""
    target_q = condition.get("q")
    if target_q is None:
        return True
    val = answers.get(target_q)
    if val is None or val == "" or val == "— bitte auswählen —":
        return False

    # Normalize boolean answers: "Ja"/"Nein" → True/False
    if isinstance(val, str) and val in ("Ja", "Nein"):
        val_norm = (val == "Ja")
    else:
        val_norm = val

    if "gt" in condition:
        try:
            return float(val_norm) > float(condition["gt"])
        except (TypeError, ValueError):
            return False
    if "lt" in condition:
        try:
            return float(val_norm) < float(condition["lt"])
        except (TypeError, ValueError):
            return False
    if "eq" in condition:
        return val_norm == condition["eq"]
    if "neq" in condition:
        return val_norm != condition["neq"]
    return True


def is_question_visible(question: dict, answers: dict) -> bool:
    """Prüft ob eine Frage im aktuellen State angezeigt werden soll."""
    show_if = question.get("show_if")
    if not show_if:
        return True
    return evaluate_condition(show_if, answers)


# ──────────────────────────────────────────────────────────────────────────
# Progress & Validation
# ──────────────────────────────────────────────────────────────────────────
def is_answered(answer: Any) -> bool:
    """Heuristik: wurde diese Frage beantwortet?"""
    if answer is None:
        return False
    if isinstance(answer, str):
        return answer.strip() != "" and answer != "— bitte auswählen —"
    if isinstance(answer, list):
        return len(answer) > 0
    return True


def calculate_progress(schema: dict, answers: dict) -> dict:
    """Returns: {total_visible, answered, pct, missing_required, all_visible_qids}."""
    total_visible = 0
    answered = 0
    missing_required = []
    visible_qids = []

    for cat in schema["categories"]:
        for q in cat["questions"]:
            if not is_question_visible(q, answers):
                continue
            total_visible += 1
            visible_qids.append(q["id"])
            ans = answers.get(q["id"])
            if is_answered(ans):
                answered += 1
            elif q.get("required"):
                missing_required.append(q["id"])

    pct = int(round((answered / total_visible * 100))) if total_visible > 0 else 0
    return {
        "total_visible": total_visible,
        "answered": answered,
        "pct": pct,
        "missing_required": missing_required,
        "visible_qids": visible_qids,
    }


def validate_answers(schema: dict, answers: dict) -> tuple[bool, list[str]]:
    """Validiert die Antworten. Returns (is_valid, errors)."""
    errors = []
    progress = calculate_progress(schema, answers)

    # Required fields
    if progress["missing_required"]:
        for qid in progress["missing_required"]:
            errors.append(f"Pflichtfeld {qid} ist leer")

    # Sum-check: Portfolio %s must add up to 100%
    portfolio_qs = ["2.2", "2.3", "2.4"]
    if all(is_answered(answers.get(q)) for q in portfolio_qs):
        total_pct = sum(float(answers.get(q, 0) or 0) for q in portfolio_qs)
        if abs(total_pct - 100) > 0.5:
            errors.append(
                f"Portfolio-Anteile (WEG + Miet + Sondereigentum) müssen 100% ergeben "
                f"(aktuell {total_pct:.0f}%)"
            )

    return (len(errors) == 0, errors)


# ──────────────────────────────────────────────────────────────────────────
# Flag Evaluation
# ──────────────────────────────────────────────────────────────────────────
def evaluate_flag_rule(rule: dict, answer: Any) -> dict | None:
    """Wertet eine flag_rule gegen eine Antwort aus. Returns flag dict oder None."""
    if rule is None or not is_answered(answer):
        return None

    # Normalize boolean
    if isinstance(answer, str) and answer in ("Ja", "Nein"):
        answer = (answer == "Ja")

    # Numeric comparisons
    def as_num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    n = as_num(answer)

    # Red conditions (highest priority)
    if "red_if_gt" in rule and n is not None and n > rule["red_if_gt"]:
        return {"level": "red", "text": rule.get("red_text", "Rote Markierung")}
    if "red_if_lt" in rule and n is not None and n < rule["red_if_lt"]:
        return {"level": "red", "text": rule.get("red_text", "Rote Markierung")}
    if "red_if_eq" in rule and answer == rule["red_if_eq"]:
        return {"level": "red", "text": rule.get("red_text", "Rote Markierung")}
    if "red_if" in rule and answer is rule["red_if"]:
        return {"level": "red", "text": rule.get("red_text", "Rote Markierung")}

    # Yellow conditions
    if "yellow_if_gt" in rule and n is not None and n > rule["yellow_if_gt"]:
        return {"level": "yellow", "text": rule.get("yellow_text", "Gelbe Markierung")}
    if "yellow_if_lt" in rule and n is not None and n < rule["yellow_if_lt"]:
        return {"level": "yellow", "text": rule.get("yellow_text", "Gelbe Markierung")}
    if "yellow_if_eq" in rule and answer == rule["yellow_if_eq"]:
        return {"level": "yellow", "text": rule.get("yellow_text", "Gelbe Markierung")}
    if "yellow_if" in rule and answer is rule["yellow_if"]:
        return {"level": "yellow", "text": rule.get("yellow_text", "Gelbe Markierung")}

    # Green conditions
    if "green_if_gt" in rule and n is not None and n > rule["green_if_gt"]:
        return {"level": "green", "text": rule.get("green_text", "Positiv")}
    if "green_if_lt" in rule and n is not None and n < rule["green_if_lt"]:
        return {"level": "green", "text": rule.get("green_text", "Positiv")}
    if "green_if" in rule and answer is rule["green_if"]:
        return {"level": "green", "text": rule.get("green_text", "Positiv")}

    return None


def evaluate_flags_for_target(schema: dict, answers: dict) -> list[dict]:
    """Wertet alle flag_rules aus und liefert die getroffenen Flags."""
    flags = []
    for cat in schema["categories"]:
        for q in cat["questions"]:
            if not is_question_visible(q, answers):
                continue
            rule = q.get("flag_rule")
            if not rule:
                continue
            flag = evaluate_flag_rule(rule, answers.get(q["id"]))
            if flag:
                flags.append(flag)
    return flags


def evaluate_knockouts_from_answers(answers: dict) -> dict:
    """Liefert das knockouts-Dict für die Target-Struktur."""
    def to_bool(qid):
        a = answers.get(qid)
        if isinstance(a, str) and a in ("Ja", "Nein"):
            return a == "Ja"
        return bool(a) if a is not None else False

    return {
        "weg_proceedings": to_bool("7.1"),
        "gf_recalled": to_bool("7.2"),
        "insolvency": to_bool("7.3"),
        "labor_lawsuits": to_bool("7.4"),
        "trustee_loss": to_bool("7.5") or to_bool("6.10"),
        "gdpr_violations": to_bool("7.6"),
    }


# ──────────────────────────────────────────────────────────────────────────
# Coercion & Mapping
# ──────────────────────────────────────────────────────────────────────────
def coerce_answer(question: dict, answer: Any) -> Any:
    """Konvertiert raw Form-Antwort in den richtigen Typ für das Target-Modell."""
    if not is_answered(answer):
        return None

    t = question.get("type")
    if t == "boolean":
        if isinstance(answer, str):
            return answer == "Ja"
        return bool(answer)
    if t == "number":
        try:
            f = float(answer)
            return int(f) if f.is_integer() else f
        except (TypeError, ValueError):
            return None
    return answer


def form_answers_to_target(
    answers: dict,
    schema: dict,
    target_id: str,
    completion_pct: int,
) -> dict:
    """Konvertiert Form-Antworten in eine vollständige Target-Struktur."""
    today = str(date.today())

    # Initialize empty nested structure
    target = {
        "id": target_id,
        "name": "",
        "location": "",
        "intake_completed_pct": completion_pct,
        "created_at": today,
        "last_updated": today,
        "company_basics": {},
        "portfolio": {},
        "customers": {},
        "operations": {},
        "people": {},
        "financials": {},
        "knockouts": {},
    }

    # Build question lookup for type info
    q_lookup = {}
    for cat in schema["categories"]:
        for q in cat["questions"]:
            q_lookup[q["id"]] = q

    # Map every answered question to its target path
    for qid, raw_answer in answers.items():
        q = q_lookup.get(qid)
        if not q:
            continue
        coerced = coerce_answer(q, raw_answer)
        if coerced is None:
            continue
        path = QUESTION_TO_TARGET_PATH.get(qid)
        if not path:
            continue
        if len(path) == 1:
            target[path[0]] = coerced
        elif len(path) == 2:
            target[path[0]][path[1]] = coerced

    # Always populate knockouts (defaults False)
    target["knockouts"] = evaluate_knockouts_from_answers(answers)

    # Stage decision
    if completion_pct >= 100:
        target["status"] = "DD"
        target["stage_history"] = [
            {"stage": "Outreach", "entered_at": today},
            {"stage": "DD", "entered_at": today},
        ]
    else:
        target["status"] = "Outreach"
        target["stage_history"] = [{"stage": "Outreach", "entered_at": today}]

    # Note: Scores and Flags werden NICHT mehr persistiert.
    # Sie werden live aus den Target-Daten berechnet (lib.scoring).

    # Fallback values to prevent dashboard crashes
    _fill_required_defaults(target)

    return target


def _fill_required_defaults(target: dict):
    """Setzt Default-Werte für Felder, die der Dashboard für die Berechnung braucht."""
    # Portfolio defaults
    p = target["portfolio"]
    p.setdefault("units_total", 0)
    p.setdefault("weg_pct", 0)
    p.setdefault("miet_pct", 0)
    p.setdefault("sondereig_pct", 0)
    p.setdefault("gewerbe_pct", 0)
    p.setdefault("weg_count", 1)
    p.setdefault("geo_spread_km", 0)
    p.setdefault("main_location_concentration", True)

    # People defaults
    pp = target["people"]
    pp.setdefault("fte_property_manager", 1)
    pp.setdefault("fte_accounting", 1)
    pp.setdefault("fte_other", 0)
    pp.setdefault("avg_pm_salary", 0)
    pp.setdefault("personnel_cost_ratio", 0)
    pp.setdefault("turnover_12m_pct", 0)
    pp.setdefault("open_vacancies", 0)
    pp.setdefault("key_person_risk", False)
    pp.setdefault("employees_over_60", 0)

    # Customers defaults
    c = target["customers"]
    c.setdefault("active_contracts", 0)
    c.setdefault("top1_pct", 0)
    c.setdefault("top3_pct", 0)
    c.setdefault("avg_contract_years", 0)
    c.setdefault("cancellation_months", 0)
    c.setdefault("nrr_12m", 100)
    c.setdefault("contracts_lost_24m", 0)
    c.setdefault("units_lost_24m", 0)
    c.setdefault("stickiness_pct", 0)
    c.setdefault("last_price_increase_year", 2020)
    c.setdefault("last_price_increase_pct", 0)

    # Operations defaults
    o = target["operations"]
    o.setdefault("primary_software", "Sonstige")
    o.setdefault("deployment", "Cloud")
    o.setdefault("software_age_years", 0)
    o.setdefault("owner_portal", False)
    o.setdefault("digital_owner_pct", 0)
    o.setdefault("banking_integration", "Manuell")
    o.setdefault("accounting_internal", True)
    o.setdefault("tool_count", 1)
    o.setdefault("it_documentation", False)

    # Financials defaults — wichtig für derived metrics
    f = target["financials"]
    f.setdefault("revenue_y1", 1)
    f.setdefault("revenue_y2", 1)
    f.setdefault("revenue_y3", 1)
    f.setdefault("ebitda_y1", 0)
    f.setdefault("ebitda_y2", 0)
    f.setdefault("ebitda_y3", 0)
    f.setdefault("existing_debt", 0)
    f.setdefault("ar_over_90d", 0)
    f.setdefault("trustee_funds", 0)

    # Company basics defaults
    cb = target["company_basics"]
    cb.setdefault("founded", 2000)
    cb.setdefault("legal_form", "GmbH")
    cb.setdefault("fte_total", 1)
    cb.setdefault("shareholders", 1)
    cb.setdefault("majority_shareholder", True)
    cb.setdefault("owner_age", 50)
    cb.setdefault("sale_motivation", "Andere")
    cb.setdefault("transition_period", "12-24 Monate")

    # Top-level
    if not target.get("name"):
        target["name"] = "Neues Target (unbenannt)"
    if not target.get("location"):
        target["location"] = "—"


# ──────────────────────────────────────────────────────────────────────────
# Preliminary Scoring (now: Full Scoring Engine via lib.scoring)
# ──────────────────────────────────────────────────────────────────────────
def compute_preliminary_scores(target: dict, answers: dict) -> dict:
    """
    Verwendet die volle Scoring-Engine aus lib.scoring.
    Liefert das legacy 5-Felder Format für Backwards-Compat
    (target["scores"] = {strategic_fit, financial_health, ...}).
    """
    # Lazy import um zirkuläre Imports zu vermeiden
    from lib.scoring import compute_legacy_scores
    return compute_legacy_scores(target)
