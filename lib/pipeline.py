"""
Buena Piloto — Pipeline Stage Logic
Definiert die 3 Pipeline-Stages und welche Pages pro Stage zugänglich sind.
"""
import streamlit as st
from datetime import date


# ──────────────────────────────────────────────────────────────────────────
# Stage Definitions
# ──────────────────────────────────────────────────────────────────────────
PIPELINE_STAGES = ["Outreach", "DD", "Offer Accepted"]
STAGE_ORDER = {stage: idx for idx, stage in enumerate(PIPELINE_STAGES)}

STAGE_CONFIG = {
    "Outreach": {
        "color": "#60A5FA",
        "bg": "#EFF6FF",
        "icon": "📨",
        "next": "DD",
        "next_label": "Move to DD",
        "description": "Erstkontakt + Intake-Phase. Seller füllt DD-Fragebogen aus.",
    },
    "DD": {
        "color": "#F59E0B",
        "bg": "#FEF3C7",
        "icon": "🔍",
        "next": "Offer Accepted",
        "next_label": "Mark as Offer Accepted",
        "description": "Due Diligence + LBO-Modeling. Investment Committee Decision pending.",
    },
    "Offer Accepted": {
        "color": "#10B981",
        "bg": "#D1FAE5",
        "icon": "🤝",
        "next": None,
        "next_label": None,
        "description": "Deal abgeschlossen. PMI-Phase aktiv.",
    },
}


# ──────────────────────────────────────────────────────────────────────────
# Page Access Rules
# ──────────────────────────────────────────────────────────────────────────
PAGE_REQUIREMENTS = {
    "Target Detail": {"min_stage": "Outreach", "always_available": True},
    "LBO Model": {"min_stage": "DD"},
    "PMI Playbook": {"min_stage": "Offer Accepted"},
}


def can_access_page(page_name: str, current_stage: str) -> bool:
    """Prüft, ob eine Page beim gegebenen Stage zugänglich ist."""
    req = PAGE_REQUIREMENTS.get(page_name)
    if not req:
        return True
    if req.get("always_available"):
        return True
    min_stage = req["min_stage"]
    return STAGE_ORDER.get(current_stage, -1) >= STAGE_ORDER.get(min_stage, 999)


def stage_gate_screen(page_name: str, target: dict):
    """Locked-Page-UI mit Hinweis welche Stage erforderlich ist."""
    current_stage = target["status"]
    req_stage = PAGE_REQUIREMENTS[page_name]["min_stage"]

    st.title(f"🔒 {page_name}")
    st.error(
        f"**Locked.** Diese Seite ist erst ab Pipeline-Stage `{req_stage}` zugänglich.\n\n"
        f"**{target['name']}** befindet sich aktuell in `{current_stage}`."
    )
    st.markdown(
        f"### Was muss passieren, um {page_name} freizuschalten?"
    )

    # Render path of stages required
    cols = st.columns(len(PIPELINE_STAGES))
    for i, stg in enumerate(PIPELINE_STAGES):
        cfg = STAGE_CONFIG[stg]
        is_current = stg == current_stage
        is_required = stg == req_stage
        is_done = STAGE_ORDER[stg] < STAGE_ORDER[current_stage]

        with cols[i]:
            if is_done:
                st.success(f"✅ **{cfg['icon']} {stg}**\nAbgeschlossen")
            elif is_current:
                st.info(f"📍 **{cfg['icon']} {stg}**\n(aktuell)")
            elif STAGE_ORDER[stg] <= STAGE_ORDER[req_stage]:
                st.warning(f"⏳ **{cfg['icon']} {stg}**\nausstehend")
            else:
                st.markdown(f"⚪ {cfg['icon']} {stg}")

    st.markdown("---")
    st.markdown(
        f"💡 **Tipp:** Gehe zurück zum Internal Dashboard und nutze die "
        f"**Stage-Transition-Buttons**, um dieses Target weiter zu bewegen."
    )
    if st.button("← Zurück zum Internal Dashboard", type="primary"):
        st.switch_page("app.py")


# ──────────────────────────────────────────────────────────────────────────
# Stage Transitions
# ──────────────────────────────────────────────────────────────────────────
def advance_target_stage(target_id: str):
    """Bewegt ein Target zur nächsten Pipeline-Stage (mutiert session_state)."""
    targets = st.session_state.get("targets_state", [])
    for t in targets:
        if t["id"] == target_id:
            current = t["status"]
            next_stage = STAGE_CONFIG[current].get("next")
            if next_stage:
                t["status"] = next_stage
                t["last_updated"] = str(date.today())
                t.setdefault("stage_history", []).append({
                    "stage": next_stage,
                    "entered_at": str(date.today()),
                })
                return next_stage
    return None


def reset_target_stage(target_id: str):
    """Setzt ein Target zurück auf Outreach (für Demo-Reset)."""
    targets = st.session_state.get("targets_state", [])
    for t in targets:
        if t["id"] == target_id:
            t["status"] = "Outreach"
            t["last_updated"] = str(date.today())
            t["stage_history"] = [{"stage": "Outreach", "entered_at": str(date.today())}]
            return True
    return False


def render_stage_pill(stage: str) -> str:
    """HTML-Pill für die Stage-Anzeige (inline use)."""
    cfg = STAGE_CONFIG.get(stage, {"color": "#6B7280", "bg": "#F3F4F6", "icon": "•"})
    color = cfg["color"]
    bg = cfg["bg"]
    icon = cfg["icon"]
    return (
        f"<span style='background:{bg};color:{color};"
        f"padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;'>"
        f"{icon} {stage}</span>"
    )
