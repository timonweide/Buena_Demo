"""
PMI Playbook — mit Auto-Plan-Generation
- Locked unless stage = Offer Accepted
- Tasks dynamisch aus DD-Findings generiert/modifiziert
- Auto-Plan-Toggle zum Vergleich Base vs. Adapted
"""
import streamlit as st
from datetime import date, timedelta
from lib.data_loader import load_pmi_template, get_active_target
from lib.pipeline import can_access_page, stage_gate_screen, render_stage_pill
from lib.pmi_auto import generate_auto_plan, count_auto_tasks

st.set_page_config(page_title="PMI Playbook · Buena Piloto", page_icon="🛠️", layout="wide")
# Auth Gate
if not st.session_state.get("authenticated"):
    st.switch_page("pages/4_👤_Seller_Portal.py")



# ──────────────────────────────────────────────────────────────────────────
# Active Target + Stage Gate
# ──────────────────────────────────────────────────────────────────────────
target = get_active_target()
if target is None:
    st.error("Keine Targets in der Pipeline.")
    if st.button("→ Seller Portal"):
        st.switch_page("pages/4_👤_Seller_Portal.py")
    st.stop()

if not can_access_page("PMI Playbook", target["status"]):
    stage_gate_screen("PMI Playbook", target)
    st.stop()

base_template = load_pmi_template()

# ──────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
with col1:
    st.title("🛠️ PMI Playbook")
    st.markdown(
        f"Target: **{target['name']}**  ·  Stage: {render_stage_pill(target['status'])}",
        unsafe_allow_html=True,
    )
with col2:
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("app.py")

# ──────────────────────────────────────────────────────────────────────────
# Auto-Plan Toggle
# ──────────────────────────────────────────────────────────────────────────
auto_state_key = f"pmi_use_auto_{target['id']}"
if auto_state_key not in st.session_state:
    st.session_state[auto_state_key] = True

col_toggle, col_info = st.columns([1, 4])
with col_toggle:
    use_auto = st.toggle(
        "🤖 Auto-Plan aktiv",
        value=st.session_state[auto_state_key],
        key=f"_toggle_{target['id']}",
        help="Wenn aktiv: Tasks werden basierend auf DD-Findings dynamisch hinzugefügt/modifiziert.",
    )
    if use_auto != st.session_state[auto_state_key]:
        st.session_state[auto_state_key] = use_auto
        st.rerun()

# Generate plan
if use_auto:
    plan = generate_auto_plan(base_template, target)
else:
    plan = base_template
    plan["applied_rules"] = []
    plan["auto_plan_active"] = False

owner_options = plan["owner_options"]
counts = count_auto_tasks(plan)
total_added = sum(c["added"] for c in counts.values())
total_modified = sum(c["modified"] for c in counts.values())

with col_info:
    if use_auto and total_added + total_modified > 0:
        st.success(
            f"🤖 **Auto-Plan aktiv:** {total_added} Tasks hinzugefügt, "
            f"{total_modified} Tasks modifiziert basierend auf DD-Findings"
        )
    elif use_auto:
        st.info("🤖 Auto-Plan aktiv — keine zusätzlichen Risiken aus DD identifiziert (clean Deal)")
    else:
        st.warning("🤖 Auto-Plan **deaktiviert** — Base-Playbook wird verwendet")

# Show applied rules
if plan.get("applied_rules"):
    with st.expander(f"📋 {len(plan['applied_rules'])} Auto-Regeln angewendet (klicken für Details)"):
        for rule in plan["applied_rules"]:
            st.markdown(f"**{rule['trigger_text']}**")
            details = []
            if rule["tasks_added"]:
                details.append(f"➕ {len(rule['tasks_added'])} Tasks hinzugefügt: `{', '.join(rule['tasks_added'])}`")
            if rule["tasks_modified"]:
                details.append(f"✏️ {len(rule['tasks_modified'])} Tasks modifiziert: `{', '.join(rule['tasks_modified'])}`")
            for d in details:
                st.caption(d)
            st.divider()

# ──────────────────────────────────────────────────────────────────────────
# Closing Date
# ──────────────────────────────────────────────────────────────────────────
closing_date = st.date_input(
    "Closing-Datum (Day 0)",
    value=date.today() + timedelta(days=30),
    help="Alle 'Tage nach Closing' rechnen ab diesem Datum.",
)

# ──────────────────────────────────────────────────────────────────────────
# Task State Initialization
# ──────────────────────────────────────────────────────────────────────────
# Note: state-key INCLUDES auto-flag, so toggling regenerates state cleanly
state_key = f"pmi_state_{target['id']}_{'auto' if use_auto else 'base'}"
if state_key not in st.session_state:
    st.session_state[state_key] = {}
    for ws in plan["workstreams"]:
        for task in ws["tasks"]:
            st.session_state[state_key][task["id"]] = {
                "status": "Open",
                "owner": task["default_owner"],
                "notes_user": "",
            }
state = st.session_state[state_key]

# Make sure every plan-task has an entry (when auto-plan adds new ones)
for ws in plan["workstreams"]:
    for task in ws["tasks"]:
        if task["id"] not in state:
            state[task["id"]] = {
                "status": "Open",
                "owner": task["default_owner"],
                "notes_user": "",
            }

# ──────────────────────────────────────────────────────────────────────────
# Progress Summary
# ──────────────────────────────────────────────────────────────────────────
all_task_ids = [t["id"] for ws in plan["workstreams"] for t in ws["tasks"]]
total_tasks = len(all_task_ids)
done_tasks = sum(1 for tid in all_task_ids if state.get(tid, {}).get("status") == "Done")
in_progress_tasks = sum(1 for tid in all_task_ids if state.get(tid, {}).get("status") == "In Progress")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Tasks", total_tasks)
c2.metric("Done", done_tasks, delta=f"{done_tasks/total_tasks*100:.0f}%" if total_tasks else "0%")
c3.metric("In Progress", in_progress_tasks)
c4.metric("Open", total_tasks - done_tasks - in_progress_tasks)
st.progress(done_tasks / total_tasks if total_tasks > 0 else 0)

st.divider()

# ──────────────────────────────────────────────────────────────────────────
# Workstreams
# ──────────────────────────────────────────────────────────────────────────
status_options = ["Open", "In Progress", "Done", "Blocked"]
status_emoji = {"Open": "⚪", "In Progress": "🟡", "Done": "✅", "Blocked": "🔴"}

for ws in plan["workstreams"]:
    ws_done = sum(1 for t in ws["tasks"] if state.get(t["id"], {}).get("status") == "Done")
    ws_total = len(ws["tasks"])
    ws_count = counts.get(ws["id"], {"added": 0, "modified": 0})
    auto_badge = ""
    if ws_count["added"] + ws_count["modified"] > 0:
        auto_badge = (
            f"<span style='background:#A855F7;color:white;font-size:10px;"
            f"padding:2px 8px;border-radius:8px;margin-left:10px;'>"
            f"+{ws_count['added']} ~{ws_count['modified']} AUTO</span>"
        )

    st.markdown(
        f"<h3 style='color:{ws['color']};margin-bottom:0;'>"
        f"{ws['icon']} {ws['name']} "
        f"<span style='font-size:14px;color:#6B7280;font-weight:normal;'>"
        f"({ws_done}/{ws_total})</span>"
        f"{auto_badge}"
        f"</h3>",
        unsafe_allow_html=True,
    )
    st.caption(ws["description"])

    for task in ws["tasks"]:
        task_state = state[task["id"]]
        status = task_state["status"]

        # Build task badge
        badges = []
        if task.get("auto_generated"):
            badges.append("🤖 AUTO-NEW")
        if task.get("auto_modified"):
            badges.append("🤖 AUTO-MODIFIED")
        badge_str = " · ".join(f"`{b}`" for b in badges)
        if badge_str:
            badge_str = " " + badge_str

        header = (
            f"{status_emoji[status]} **{task['id']}** — {task['name']}"
            f"{badge_str}  ·  `{task_state['owner']}` · Day {task['timing_days_after_close']}"
        )

        with st.expander(header, expanded=False):
            cols = st.columns([2, 2, 1])

            with cols[0]:
                st.markdown(f"**Owner**")
                try:
                    owner_idx = owner_options.index(task_state["owner"])
                except ValueError:
                    # Custom owner from auto-plan that isn't in default options
                    owner_options_local = owner_options + [task_state["owner"]]
                    owner_idx = owner_options_local.index(task_state["owner"])
                    new_owner = st.selectbox(
                        "Owner",
                        options=owner_options_local,
                        index=owner_idx,
                        key=f"owner_{state_key}_{task['id']}",
                        label_visibility="collapsed",
                    )
                    state[task["id"]]["owner"] = new_owner
                else:
                    new_owner = st.selectbox(
                        "Owner",
                        options=owner_options,
                        index=owner_idx,
                        key=f"owner_{state_key}_{task['id']}",
                        label_visibility="collapsed",
                    )
                    state[task["id"]]["owner"] = new_owner

            with cols[1]:
                st.markdown(f"**Status**")
                new_status = st.selectbox(
                    "Status",
                    options=status_options,
                    index=status_options.index(status),
                    key=f"status_{state_key}_{task['id']}",
                    label_visibility="collapsed",
                )
                state[task["id"]]["status"] = new_status

            with cols[2]:
                st.markdown(f"**Timing**")
                st.caption(f"Day {task['timing_days_after_close']} after closing")

            st.divider()
            st.markdown(f"**Dependencies:** {task['dependencies']}")
            st.markdown(f"**Acceptance Criteria:** {task['acceptance_criteria']}")
            st.info(f"💡 {task['notes']}", icon="📝")

            user_note = st.text_area(
                "Eigene Notizen / Updates",
                value=task_state["notes_user"],
                key=f"notes_{state_key}_{task['id']}",
                height=80,
                placeholder="z.B. 'Termin mit Steuerberater am 15.05., reconcile zu 99.7%'",
            )
            state[task["id"]]["notes_user"] = user_note

    st.divider()
