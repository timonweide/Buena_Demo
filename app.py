"""
Buena Piloto — Internal Dashboard
Kanban-Pipeline + Active Target Cockpit
"""
from datetime import date
import streamlit as st
from lib.data_loader import (
    load_targets,
    get_active_target,
    calculate_derived_metrics,
    get_flag_emoji,
    reset_all_data,
)
from lib.pipeline import (
    PIPELINE_STAGES,
    STAGE_CONFIG,
    advance_target_stage,
    reset_target_stage,
    render_stage_pill,
    can_access_page,
)
from lib.scoring import has_knockouts, compute_legacy_scores

st.set_page_config(
    page_title="Buena Piloto · Internal",
    page_icon="🛩️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────
# Auth Gate — unauthenticated users see Seller Portal
# ──────────────────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    st.switch_page("pages/4_👤_Seller_Portal.py")

# ──────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .stage-col-header {
        padding: 8px 14px;
        border-radius: 8px 8px 0 0;
        color: white !important;
        font-weight: 700;
        font-size: 14px;
    }
    .target-card {
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        background: white !important;
        color: #111827 !important;
    }
    .target-card-active {
        border: 2px solid #3B82F6;
        background: #EFF6FF !important;
    }
    .target-card-name {
        font-weight: 700;
        font-size: 14px;
        color: #111827 !important;
    }
    .target-card-meta {
        font-size: 11px;
        color: #6B7280 !important;
        margin-top: 4px;
    }
    .target-card-meta b { color: #111827 !important; }
    [data-testid="stMetricValue"] { font-size: 26px; }
    .progress-mini {
        background: #F3F4F6;
        border-radius: 4px;
        height: 6px;
        margin-top: 6px;
        overflow: hidden;
    }
    .progress-mini-fill {
        background: #3B82F6;
        height: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────
col_title, col_meta = st.columns([4, 1])
with col_title:
    st.title("🛩️ Buena Piloto")
    st.caption("Internal Dashboard · Acquisition & Integration Cockpit")
with col_meta:
    st.markdown(
        "<div style='text-align:right;padding-top:30px;color:#6B7280;font-size:13px;'>"
        "v0.3 · Pipeline-driven"
        "</div>",
        unsafe_allow_html=True,
    )

# Init state
targets = load_targets()
if "active_target_id" not in st.session_state:
    st.session_state["active_target_id"] = targets[0]["id"]

# ──────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("🎯 Active Target")
    target_names = {t["id"]: t["name"] for t in targets}
    target_ids = list(target_names.keys())

    # Find current index based on active_target_id (separate key from widget!)
    current_id = st.session_state["active_target_id"]
    try:
        current_idx = target_ids.index(current_id)
    except ValueError:
        current_idx = 0
        st.session_state["active_target_id"] = target_ids[0]

    selected_id = st.selectbox(
        "Switch target",
        options=target_ids,
        index=current_idx,
        format_func=lambda tid: target_names[tid],
        key="_sidebar_target_select",  # ← separate widget key
    )
    # Sync widget choice → session_state
    if selected_id != st.session_state["active_target_id"]:
        st.session_state["active_target_id"] = selected_id
        st.rerun()

    sel = next(t for t in targets if t["id"] == selected_id)
    sel_score = compute_legacy_scores(sel)["overall_score"]
    st.markdown(
        f"**Stage:** {render_stage_pill(sel['status'])}",
        unsafe_allow_html=True,
    )
    st.markdown(f"**Score:** **{sel_score}** / 100")
    st.markdown(f"**Last Update:** {sel['last_updated']}")
    st.divider()

    st.markdown("**Page Access (current stage)**")
    pages_check = [
        ("📊 Target Detail", "Target Detail"),
        ("💰 LBO Model", "LBO Model"),
        ("🛠️ PMI Playbook", "PMI Playbook"),
    ]
    for label, page_key in pages_check:
        accessible = can_access_page(page_key, sel["status"])
        st.markdown(f"{'✅' if accessible else '🔒'} {label}")

    st.divider()
    if st.button("↻ Reset Demo Data", use_container_width=True):
        reset_all_data()
        st.rerun()

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.switch_page("pages/4_👤_Seller_Portal.py")

# ──────────────────────────────────────────────────────────────────────────
# Active Target Cockpit (full width, top of page)
# ──────────────────────────────────────────────────────────────────────────
active = get_active_target()
metrics = calculate_derived_metrics(active)
has_ko, ko_list = has_knockouts(active)

st.markdown(
    f"### {active['name']}  "
    f"{render_stage_pill(active['status'])}",
    unsafe_allow_html=True,
)
st.caption(
    f"📍 {active['location']}  ·  "
    f"📐 {active['portfolio']['units_total']:,} Units  ·  "
    f"👥 {active['people']['fte_property_manager'] + active['people']['fte_accounting'] + active['people']['fte_other']} FTE  ·  "
    f"📅 Last Update: {active['last_updated']}"
)

if has_ko:
    st.error(f"🚫 Knock-Out triggered: {', '.join(ko_list)} — DD-Pause empfohlen")

# Active scores via full engine (so Sidebar weights take effect)
active_weights = st.session_state.get("scoring_weights")
active_subw = st.session_state.get("scoring_sub_weights")
active_scores = compute_legacy_scores(active)

# 4 KPI Spalten
k1, k2, k3, k4 = st.columns(4)
k1.metric("Overall Score", f"{active_scores['overall_score']} / 100")
k2.metric("Revenue (Y1)", f"€{active['financials']['revenue_y1']:,.0f}")
k3.metric("EBITDA-Marge", f"{metrics['ebitda_margin_y1']:.1f}%")
k4.metric("Units / PM", f"{metrics['units_per_pm']:.0f}",
          delta=f"vs. Buena {metrics['benchmarks']['units_per_pm_target']}")

# Stage-spezifische Anzeige
stage = active["status"]
st.markdown("---")

# Quick info section + Stage Action Buttons
col_info, col_actions = st.columns([2, 1])

with col_info:
    if stage == "Outreach":
        st.markdown("### 📨 Outreach Status")
        intake_pct = active.get("intake_completed_pct", 0)
        st.markdown(f"**Seller Intake:** {intake_pct}% completed")
        st.progress(intake_pct / 100)
        if intake_pct < 100:
            st.caption("⏳ Verkäufer hat den DD-Fragebogen noch nicht abgeschlossen")
        else:
            st.success("✅ Intake komplett — bereit für DD-Phase")

    elif stage == "DD":
        st.markdown("### 🔍 DD Status")
        st.markdown("**Top Flags:**")
        from lib.scoring import compute_live_flags as _live_flags
        active_flags = _live_flags(active)
        # Sort red > yellow > green to show most important first
        priority = {"red": 0, "yellow": 1, "green": 2}
        active_flags.sort(key=lambda f: priority.get(f["level"], 3))
        for flag in active_flags[:3]:
            emoji = get_flag_emoji(flag["level"])
            st.markdown(f"{emoji} {flag['text']}")

    elif stage == "Offer Accepted":
        st.markdown("### 🤝 Integration Status")
        # Check if PMI state exists
        pmi_state = st.session_state.get(f"pmi_state_{active['id']}", {})
        if pmi_state:
            done = sum(1 for v in pmi_state.values() if v.get("status") == "Done")
            total = len(pmi_state)
            st.markdown(f"**PMI Progress:** {done}/{total} tasks done")
            st.progress(done / total if total else 0)
        else:
            st.caption("PMI Playbook noch nicht initialisiert. Öffne die PMI-Page.")

with col_actions:
    st.markdown("### Actions")
    next_stage = STAGE_CONFIG[stage].get("next")

    if next_stage:
        if st.button(
            f"→ {STAGE_CONFIG[stage]['next_label']}",
            type="primary",
            use_container_width=True,
            key="btn_advance",
        ):
            new_stage = advance_target_stage(active["id"])
            st.toast(f"✅ Moved to **{new_stage}**", icon="🎯")
            st.rerun()
    else:
        st.success("✅ Final stage reached")

    st.markdown("**Open Page:**")
    if st.button("📊 Target Detail", use_container_width=True):
        st.switch_page("pages/1_📊_Target_Detail.py")

    if can_access_page("LBO Model", stage):
        if st.button("💰 LBO Model", use_container_width=True):
            st.switch_page("pages/2_💰_LBO_Model.py")
    else:
        st.button("🔒 LBO Model (locked)", disabled=True, use_container_width=True)

    if can_access_page("PMI Playbook", stage):
        if st.button("🛠️ PMI Playbook", use_container_width=True):
            st.switch_page("pages/3_🛠️_PMI_Playbook.py")
    else:
        st.button("🔒 PMI Playbook (locked)", disabled=True, use_container_width=True)

    if stage != "Outreach":
        if st.button("↺ Reset to Outreach", use_container_width=True, key="btn_reset"):
            reset_target_stage(active["id"])
            st.toast("Stage reset to Outreach")
            st.rerun()

    st.markdown("**Export:**")
    memo_key = f"ic_memo_pdf_{active['id']}"

    if st.button("📄 IC Memo generieren", use_container_width=True,
                 help="Generiert Investment-Committee-Memo als PDF. Benötigt `reportlab` (pip install reportlab)."):
        try:
            from lib.ic_memo import generate_ic_memo
            from lib.lbo_engine import calculate_lbo, DEFAULT_LBO_INPUTS
            from lib.pmi_auto import generate_auto_plan
            from lib.data_loader import load_pmi_template
            import json as _json

            weights = st.session_state.get("scoring_weights")
            parsed_pnl = st.session_state.get(f"ai_pnl_{active['id']}")

            lbo_inputs = None
            lbo_result = None
            if stage in ("DD", "Offer Accepted"):
                lbo_state_key = f"lbo_inputs_{active['id']}"
                lbo_inputs = st.session_state.get(lbo_state_key) or dict(DEFAULT_LBO_INPUTS)
                if parsed_pnl:
                    base_eb = parsed_pnl["subtotals"]["EBITDA"]
                    base_rev = parsed_pnl["subtotals"]["Revenue Total"]
                else:
                    base_eb = active["financials"].get("ebitda_y1", 0) or 0
                    base_rev = active["financials"].get("revenue_y1", 0) or 0
                if base_eb > 0:
                    lbo_result = calculate_lbo(lbo_inputs, base_eb, base_rev)

            pmi_plan = None
            pmi_state = None
            if stage == "Offer Accepted":
                base_template = load_pmi_template()
                use_auto = st.session_state.get(f"pmi_use_auto_{active['id']}", True)
                pmi_plan = generate_auto_plan(base_template, active) if use_auto else base_template
                pmi_state = (
                    st.session_state.get(f"pmi_state_{active['id']}_auto")
                    or st.session_state.get(f"pmi_state_{active['id']}_base")
                    or {}
                )

            with st.spinner("Generiere IC Memo…"):
                pdf_bytes = generate_ic_memo(
                    target=active,
                    weights=weights,
                    parsed_pnl=parsed_pnl,
                    lbo_inputs=lbo_inputs,
                    lbo_result=lbo_result,
                    pmi_plan=pmi_plan,
                    pmi_state=pmi_state,
                )
            st.session_state[memo_key] = pdf_bytes
            st.toast("✅ IC Memo generiert", icon="📄")

        except ImportError:
            st.error("❌ `reportlab` fehlt — bitte installieren: `pip install reportlab`")
        except Exception as e:
            st.error(f"❌ Fehler: {str(e)[:120]}")

    # Show download button only if PDF was already generated
    if memo_key in st.session_state:
        safe_name = active["name"].replace(" ", "_").replace("/", "_")
        st.download_button(
            "⬇️ IC Memo herunterladen",
            data=st.session_state[memo_key],
            file_name=f"IC_Memo_{safe_name}_{date.today().isoformat()}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

st.divider()

# ──────────────────────────────────────────────────────────────────────────
# Kanban Pipeline View
# ──────────────────────────────────────────────────────────────────────────
st.subheader("Pipeline")
st.caption("Klick auf eine Karte um sie als Active Target zu setzen")

stage_cols = st.columns(len(PIPELINE_STAGES))
for col, stage_name in zip(stage_cols, PIPELINE_STAGES):
    with col:
        cfg = STAGE_CONFIG[stage_name]
        cfg_color = cfg["color"]
        cfg_icon = cfg["icon"]
        targets_in_stage = [t for t in targets if t["status"] == stage_name]

        # Column Header
        st.markdown(
            f"<div class='stage-col-header' style='background:{cfg_color};'>"
            f"{cfg_icon} {stage_name} ({len(targets_in_stage)})"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.caption(cfg["description"])

        # Cards
        for t in targets_in_stage:
            is_active = t["id"] == active["id"]
            t_metrics = calculate_derived_metrics(t)

            # Show NEW badge if target was created today (from seller submission)
            today_str = str(date.today())
            is_new = t.get("created_at") == today_str and t["id"] not in (
                "tgt_001", "tgt_002", "tgt_003"
            )
            new_badge = (
                "<span style='background:#10B981;color:white;font-size:9px;"
                "padding:2px 6px;border-radius:8px;margin-left:6px;'>NEW</span>"
                if is_new else ""
            )

            extra = ""
            if stage_name == "Outreach":
                pct = t.get("intake_completed_pct", 0)
                extra = (
                    f"<div class='progress-mini'>"
                    f"<div class='progress-mini-fill' style='width:{pct}%;'></div></div>"
                    f"<div class='target-card-meta'>Intake: {pct}%</div>"
                )

            card_score = compute_legacy_scores(t)["overall_score"]
            card_html = (
                f"<div class='target-card{' target-card-active' if is_active else ''}'>"
                f"<div class='target-card-name'>{t['name']}{new_badge}</div>"
                f"<div class='target-card-meta'>📍 {t['location']} · "
                f"{t['portfolio']['units_total']:,} Units · "
                f"EBITDA-Marge {t_metrics['ebitda_margin_y1']:.1f}%</div>"
                f"<div class='target-card-meta'>Score: <b>{card_score}</b></div>"
                f"{extra}"
                f"</div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)

            # Action button below card
            if is_active:
                st.caption("📍 Currently active")
            else:
                if st.button(
                    "Set as active",
                    key=f"select_{t['id']}",
                    use_container_width=True,
                ):
                    st.session_state["active_target_id"] = t["id"]
                    st.rerun()

# ──────────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Buena Piloto · Acquisition & Integration Cockpit · "
    "Take-Home Submission Timon Weidemann · Mai 2026"
)
