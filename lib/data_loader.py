"""
Buena Piloto — Data Loader
Lädt Mock-Daten beim ersten Aufruf in session_state.
Mutationen (Stage-Transitionen) persistieren innerhalb der Session.
Tag 6: Migration auf SQLite für echte Persistenz.
"""
import json
import streamlit as st
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def init_targets_state():
    """Lädt targets.json einmalig in session_state."""
    if "targets_state" not in st.session_state:
        with open(DATA_DIR / "targets.json", "r", encoding="utf-8") as f:
            st.session_state["targets_state"] = json.load(f)["targets"]


def load_targets() -> list[dict]:
    """Liefert die aktuell in session_state gespeicherten Targets."""
    init_targets_state()
    return st.session_state["targets_state"]


@st.cache_data
def load_dd_schema() -> dict:
    """Lädt das DD-Fragenschema aus dd_schema.json."""
    with open(DATA_DIR / "dd_schema.json", "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_pmi_template() -> dict:
    """Lädt die PMI-Workstreams-Template aus pmi_tasks_template.json."""
    with open(DATA_DIR / "pmi_tasks_template.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_target_by_id(target_id: str) -> dict | None:
    """Liefert ein einzelnes Target nach ID (aus session_state)."""
    targets = load_targets()
    return next((t for t in targets if t["id"] == target_id), None)


def add_target(target: dict) -> str:
    """Fügt ein neues Target dem session_state hinzu. Returns die ID."""
    init_targets_state()
    # Generate unique ID if not provided
    existing_ids = {t["id"] for t in st.session_state["targets_state"]}
    if not target.get("id") or target["id"] in existing_ids:
        i = len(st.session_state["targets_state"]) + 1
        while f"tgt_{i:03d}" in existing_ids:
            i += 1
        target["id"] = f"tgt_{i:03d}"
    st.session_state["targets_state"].append(target)
    return target["id"]


def get_active_target() -> dict | None:
    """Liefert das aktuell ausgewählte Target.
    Defensive: Wenn keine ID gesetzt oder ID ungültig, fällt automatisch
    auf das erste Target zurück (verhindert leere Pages bei Seitenwechsel/Refresh).
    """
    targets = load_targets()
    if not targets:
        return None
    active_id = st.session_state.get("active_target_id")
    if active_id:
        found = next((t for t in targets if t["id"] == active_id), None)
        if found:
            return found
    # Fallback: ersten verfügbaren Target nehmen UND als active setzen
    fallback = targets[0]
    st.session_state["active_target_id"] = fallback["id"]
    return fallback


def reset_all_data():
    """Reload aller Targets aus targets.json — für Demo-Reset."""
    if "targets_state" in st.session_state:
        del st.session_state["targets_state"]
    # Auch alle PMI-States zurücksetzen
    keys_to_clear = [k for k in st.session_state.keys() if k.startswith("pmi_state_")]
    for k in keys_to_clear:
        del st.session_state[k]


def get_score_color(score: int) -> str:
    """Score → Farbe für visuelles Feedback."""
    if score >= 70:
        return "#10B981"
    elif score >= 50:
        return "#F59E0B"
    else:
        return "#EF4444"


def get_flag_emoji(level: str) -> str:
    """Flag-Level → Emoji."""
    return {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(level, "⚪")


def calculate_derived_metrics(target: dict) -> dict:
    """
    Berechnet abgeleitete Metriken aus den Roh-Antworten.
    Per Linus' Anmerkung: Was berechnet werden kann, wird nicht abgefragt.
    Defensive: Verwendet .get() mit Defaults für neu submittete Targets.
    """
    p = target.get("portfolio", {})
    pp = target.get("people", {})
    f = target.get("financials", {})

    units = p.get("units_total", 0) or 0
    fte_pm = pp.get("fte_property_manager", 0) or 0
    fte_acc = pp.get("fte_accounting", 0) or 0
    fte_other = pp.get("fte_other", 0) or 0
    fte_total = fte_pm + fte_acc + fte_other

    weg_pct = p.get("weg_pct", 0) or 0
    weg_count = p.get("weg_count", 0) or 0

    rev_y1 = f.get("revenue_y1", 0) or 0
    rev_y2 = f.get("revenue_y2", 0) or 0
    rev_y3 = f.get("revenue_y3", 0) or 0
    eb_y1 = f.get("ebitda_y1", 0) or 0
    eb_y2 = f.get("ebitda_y2", 0) or 0
    eb_y3 = f.get("ebitda_y3", 0) or 0
    ar_90 = f.get("ar_over_90d", 0) or 0

    metrics = {
        "units_per_pm": units / fte_pm if fte_pm > 0 else 0,
        "units_per_accounting": units / fte_acc if fte_acc > 0 else 0,
        "units_per_total_fte": units / fte_total if fte_total > 0 else 0,
        "avg_weg_size": (units * weg_pct / 100) / weg_count if weg_count > 0 else 0,
        "revenue_per_unit_year": rev_y1 / units if units > 0 else 0,
        "revenue_per_fte": rev_y1 / fte_total if fte_total > 0 else 0,
        "ebitda_margin_y1": (eb_y1 / rev_y1 * 100) if rev_y1 > 0 else 0,
        "ebitda_margin_y2": (eb_y2 / rev_y2 * 100) if rev_y2 > 0 else 0,
        "ebitda_margin_y3": (eb_y3 / rev_y3 * 100) if rev_y3 > 0 else 0,
        "revenue_cagr_3y": (
            ((rev_y1 / rev_y3) ** (1 / 2) - 1) * 100
            if rev_y3 > 0 else 0
        ),
        "ar_over_90d_pct_revenue": (ar_90 / rev_y1 * 100) if rev_y1 > 0 else 0,
    }
    metrics["benchmarks"] = {
        "units_per_pm_target": 400,
        "units_per_accounting_target": 800,
        "ebitda_margin_buena_post_pmi": 35.0,
        "revenue_per_unit_target": 720,
    }
    return metrics
