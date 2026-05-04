"""
LBO Model — Voll-Implementierung
- Year-by-Year P&L mit Synergien
- FCF Waterfall + Debt Schedule
- Earn-Out Trigger Logic mit visuellem Highlight
- IRR/MoM Returns
- Long Holding Period (3-20J)
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from lib.data_loader import get_active_target
from lib.lbo_engine import DEFAULT_LBO_INPUTS, calculate_lbo
from lib.pipeline import can_access_page, stage_gate_screen, render_stage_pill

st.set_page_config(page_title="LBO Model · Buena Piloto", page_icon="💰", layout="wide")
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

if not can_access_page("LBO Model", target["status"]):
    stage_gate_screen("LBO Model", target)
    st.stop()

# ──────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────
base_ebitda = target["financials"]["ebitda_y1"]
base_revenue = target["financials"]["revenue_y1"]

# Check if AI-parsed P&L overrides are available
parsed_key = f"ai_pnl_{target['id']}"
parsed_pnl = st.session_state.get(parsed_key)
use_parsed = False

col1, col2 = st.columns([4, 1])
with col1:
    st.title("💰 LBO Model")
    st.markdown(
        f"Target: **{target['name']}**  ·  Stage: {render_stage_pill(target['status'])}",
        unsafe_allow_html=True,
    )
with col2:
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("app.py")

# Source toggle if AI-parsed P&L exists
if parsed_pnl:
    src_col, _ = st.columns([2, 3])
    with src_col:
        use_parsed = st.toggle(
            "📊 AI-parsed BWA-Werte verwenden",
            value=True,
            help=f"Aus BWA: EBITDA €{parsed_pnl['subtotals']['EBITDA']:,.0f} · Revenue €{parsed_pnl['subtotals']['Revenue Total']:,.0f}",
        )
    if use_parsed:
        base_ebitda = parsed_pnl["subtotals"]["EBITDA"]
        base_revenue = parsed_pnl["subtotals"]["Revenue Total"]

source_label = "BWA (AI-parsed)" if use_parsed else "Self-reported (DD)"
st.caption(
    f"Base EBITDA: **€{base_ebitda:,.0f}**  ·  "
    f"Base Revenue: **€{base_revenue:,.0f}**  ·  "
    f"Quelle: {source_label}"
)

# ──────────────────────────────────────────────────────────────────────────
# Sidebar — Input Variables (per-target persistent)
# ──────────────────────────────────────────────────────────────────────────
lbo_state_key = f"lbo_inputs_{target['id']}"
if lbo_state_key not in st.session_state:
    # Initialize from defaults, with smart Earn-Out threshold (1.2x base EBITDA)
    init = dict(DEFAULT_LBO_INPUTS)
    init["earnout_threshold_ebitda"] = int(base_ebitda * 1.2)
    st.session_state[lbo_state_key] = init

saved = st.session_state[lbo_state_key]


def lbo_widget_key(name: str) -> str:
    """Per-target widget key, scoped to active target."""
    return f"lbo_w_{target['id']}_{name}"


with st.sidebar:
    # Reset button
    if st.button("↻ Reset LBO Settings", use_container_width=True,
                 help="Setzt alle LBO-Inputs für dieses Target auf Default zurück"):
        del st.session_state[lbo_state_key]
        # Also clear all LBO widget state for this target
        for k in list(st.session_state.keys()):
            if k.startswith(f"lbo_w_{target['id']}_"):
                del st.session_state[k]
        st.rerun()

    st.subheader("Deal-Struktur")
    saved["entry_ebitda_multiple"] = st.slider(
        "Entry EBITDA Multiple", 3.0, 8.0, saved["entry_ebitda_multiple"], 0.1,
        key=lbo_widget_key("entry_multiple"),
    )
    saved["debt_pct"] = st.slider(
        "Debt % of Purchase Price", 0, 70, int(saved["debt_pct"]),
        key=lbo_widget_key("debt_pct"),
    )
    saved["interest_rate_pct"] = st.slider(
        "Interest Rate (%)", 4.0, 12.0, saved["interest_rate_pct"], 0.25,
        key=lbo_widget_key("interest_rate"),
    )
    saved["mandatory_amortization_pct"] = st.slider(
        "Mandatory Amort (% p.a.)", 0, 20, int(saved["mandatory_amortization_pct"]),
        key=lbo_widget_key("mand_amort"),
    )
    saved["tax_rate_pct"] = st.slider(
        "Tax Rate (%)", 20, 35, int(saved["tax_rate_pct"]),
        key=lbo_widget_key("tax_rate"),
    )

    st.divider()
    st.subheader("Holding & Exit")
    saved["holding_period_years"] = st.slider(
        "Holding Period (Jahre)", 3, 20, int(saved["holding_period_years"]),
        key=lbo_widget_key("holding"),
        help="Buena hält langfristig — IRR-Berechnung ist trotzdem für Vergleichbarkeit relevant."
    )
    saved["exit_ebitda_multiple"] = st.slider(
        "Exit EBITDA Multiple", 4.0, 9.0, saved["exit_ebitda_multiple"], 0.1,
        key=lbo_widget_key("exit_multiple"),
    )

    st.divider()
    st.subheader("Operating Case")
    saved["revenue_growth_pct"] = st.slider(
        "Revenue Growth p.a. (%)", 0.0, 15.0, saved["revenue_growth_pct"], 0.5,
        key=lbo_widget_key("rev_growth"),
    )
    saved["ebitda_growth_pct"] = st.slider(
        "EBITDA Growth p.a. (%)", 0.0, 25.0, saved["ebitda_growth_pct"], 0.5,
        key=lbo_widget_key("eb_growth"),
    )
    saved["synergy_y1"] = st.number_input(
        "Synergy Y1 (€)", min_value=0, value=int(saved["synergy_y1"]), step=10000,
        key=lbo_widget_key("syn_y1"),
    )
    saved["synergy_y2"] = st.number_input(
        "Synergy Y2 (€)", min_value=0, value=int(saved["synergy_y2"]), step=10000,
        key=lbo_widget_key("syn_y2"),
    )
    saved["synergy_run_rate"] = st.number_input(
        "Synergy Run-Rate ab Y3 (€)", min_value=0, value=int(saved["synergy_run_rate"]), step=10000,
        key=lbo_widget_key("syn_run"),
    )

    with st.expander("FCF Assumptions"):
        saved["da_pct_revenue"] = st.number_input(
            "D&A (% Revenue)", 0.0, 10.0, saved["da_pct_revenue"], 0.1,
            key=lbo_widget_key("da_pct"),
        )
        saved["capex_pct_revenue"] = st.number_input(
            "CapEx (% Revenue)", 0.0, 10.0, saved["capex_pct_revenue"], 0.1,
            key=lbo_widget_key("capex_pct"),
        )
        saved["nwc_change_pct_revenue"] = st.number_input(
            "ΔNWC (% Δ Revenue)", 0.0, 10.0, saved["nwc_change_pct_revenue"], 0.1,
            key=lbo_widget_key("nwc_pct"),
        )

    st.divider()
    st.subheader("🎁 Earn-Out (Mittelstand)")
    saved["earnout_amount"] = st.number_input(
        "Earn-Out Amount (€)", min_value=0, value=int(saved["earnout_amount"]), step=50000,
        key=lbo_widget_key("eo_amount"),
    )
    saved["earnout_year"] = st.slider(
        "Earn-Out Zahlungsjahr", 1, 5, int(saved["earnout_year"]),
        key=lbo_widget_key("eo_year"),
    )
    saved["earnout_threshold_ebitda"] = st.number_input(
        "EBITDA-Threshold (€)", min_value=0, value=int(saved["earnout_threshold_ebitda"]), step=10000,
        key=lbo_widget_key("eo_thr"),
    )
    saved["earnout_paid_from_fcf"] = st.checkbox(
        "Earn-Out aus operativem FCF", value=saved["earnout_paid_from_fcf"],
        key=lbo_widget_key("eo_fcf"),
        help="Wenn aktiv: reduziert FCF in Earn-Out-Jahr und verzögert Debt-Paydown."
    )

    # Save indicator
    st.caption(f"💾 Settings gespeichert für **{target['name']}**")

# ──────────────────────────────────────────────────────────────────────────
# Build Inputs + Run Engine
# ──────────────────────────────────────────────────────────────────────────
inputs = saved
result = calculate_lbo(inputs, base_ebitda, base_revenue)

# ──────────────────────────────────────────────────────────────────────────
# Sources & Uses
# ──────────────────────────────────────────────────────────────────────────
st.subheader("Sources & Uses")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Purchase Price", f"€{result['purchase_price']:,.0f}",
          help=f"= EBITDA €{base_ebitda:,.0f} × {saved['entry_ebitda_multiple']:.1f}x")
c2.metric("Debt", f"€{result['debt']:,.0f}", help=f"{int(saved['debt_pct'])}% of Purchase Price")
c3.metric("Equity (at Entry)", f"€{result['equity']:,.0f}")
if result["additional_equity_for_earnout"] > 0:
    c4.metric("Add. Equity (Earn-Out)", f"€{result['additional_equity_for_earnout']:,.0f}",
              help="Earn-Out wurde aus neuer Equity-Injection bezahlt")
else:
    c4.metric("Total Equity", f"€{result['total_equity_invested']:,.0f}")

st.divider()

# ──────────────────────────────────────────────────────────────────────────
# Returns Headline
# ──────────────────────────────────────────────────────────────────────────
st.subheader("Returns at Exit")
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Exit EBITDA (Y{int(saved['holding_period_years'])})", f"€{result['exit_ebitda']:,.0f}")
c2.metric("Exit Equity Value", f"€{result['exit_equity']:,.0f}")
c3.metric("MoM", f"{result['mom']:.2f}x")
c4.metric("IRR", f"{result['irr_pct']:.1f}%")

# Earn-Out summary
eos = result["earnout_summary"]
if saved["earnout_amount"] > 0:
    if eos["triggered"]:
        st.success(
            f"🎁 **Earn-Out triggered in Y{eos['year']}**: "
            f"€{eos['amount']:,.0f} bezahlt (Threshold €{eos['threshold']:,.0f} erreicht, "
            f"finanziert aus {eos['funded_from']})"
        )
    else:
        st.info(
            f"🎁 **Earn-Out nicht getriggert**: "
            f"EBITDA in Y{int(saved['earnout_year'])} unter Threshold €{eos['threshold']:,.0f} → keine Zahlung."
        )

st.divider()

# ──────────────────────────────────────────────────────────────────────────
# Tabs: Year-by-Year + Debt Schedule + Visualizations
# ──────────────────────────────────────────────────────────────────────────
tab_proj, tab_debt, tab_viz = st.tabs([
    "📈 Year-by-Year P&L + FCF",
    "🏦 Debt Schedule",
    "📊 Visualisierung",
])

# ── Year-by-Year P&L ──
with tab_proj:
    rows = []
    for y in result["yearly_data"]:
        rows.append({
            "Year": f"Y{y['year']}",
            "Revenue": y["revenue"],
            "EBITDA (organic)": y["ebitda_organic"],
            "Synergy": y["synergy"],
            "EBITDA (total)": y["ebitda"],
            "D&A": -y["da"],
            "EBIT": y["ebit"],
            "Interest": -y["interest_expense"],
            "Taxes": -y["taxes"],
            "Net Income": y["net_income"],
            "CapEx": -y["capex"],
            "ΔNWC": -y["nwc_change"],
            "FCF (pre Earn-Out)": y["fcf_pre_earnout"],
            "Earn-Out": -y["earnout_paid"],
            "FCF (post Earn-Out)": y["fcf_post_earnout"],
        })
    df = pd.DataFrame(rows).set_index("Year").T

    # Format all numeric values as currency with thousands separator
    fmt_df = df.map(lambda v: f"€{v:,.0f}" if isinstance(v, (int, float)) else v)
    st.dataframe(fmt_df, use_container_width=True)

    st.caption(
        "**Lesehilfe:** EBITDA = organic + Synergien · "
        "FCF = Net Income + D&A − CapEx − ΔNWC · "
        "Earn-Out reduziert FCF wenn 'aus FCF finanziert'."
    )

# ── Debt Schedule ──
with tab_debt:
    rows = []
    for y in result["yearly_data"]:
        rows.append({
            "Year": f"Y{y['year']}",
            "Beginning Debt": y["beginning_debt"],
            "Interest Expense": y["interest_expense"],
            "FCF Available": y["fcf_post_earnout"],
            "Mandatory Amort": y["mandatory_amort"],
            "Cash Sweep": y["cash_sweep"],
            "Total Debt Paydown": y["mandatory_amort"] + y["cash_sweep"],
            "Ending Debt": y["ending_debt"],
        })
    df = pd.DataFrame(rows).set_index("Year").T
    fmt_df = df.map(lambda v: f"€{v:,.0f}" if isinstance(v, (int, float)) else v)
    st.dataframe(fmt_df, use_container_width=True)

    st.caption(
        "**Mechanik:** Mandatory Amortization läuft vorrangig. "
        "Verbleibender FCF wird via Cash Sweep zur Schuldentilgung genutzt. "
        "Falls Earn-Out aus FCF kommt: weniger Cash Sweep in dem Jahr."
    )

# ── Visualization ──
with tab_viz:
    st.markdown("**EBITDA & Debt Trajectory**")
    years = [y["year"] for y in result["yearly_data"]]
    ebitdas = [y["ebitda"] for y in result["yearly_data"]]
    debts = [y["ending_debt"] for y in result["yearly_data"]]
    fcfs = [y["fcf_post_earnout"] for y in result["yearly_data"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"Y{y}" for y in years], y=ebitdas, name="EBITDA",
        marker_color="#3B82F6",
    ))
    fig.add_trace(go.Scatter(
        x=[f"Y{y}" for y in years], y=debts, name="Ending Debt",
        line=dict(color="#EF4444", width=3), mode="lines+markers", yaxis="y2",
    ))
    fig.add_trace(go.Scatter(
        x=[f"Y{y}" for y in years], y=fcfs, name="FCF (post Earn-Out)",
        line=dict(color="#10B981", width=2, dash="dot"), mode="lines+markers",
    ))
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis=dict(title="EBITDA / FCF (€)"),
        yaxis2=dict(title="Debt (€)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Equity-Werterzeugung Brücke (Entry → Exit)**")
    # Waterfall: Entry Equity → EBITDA Growth → Multiple Expansion → Debt Paydown → Earn-Out → Exit Equity
    initial_eq = result["equity"]
    additional_eq = result["additional_equity_for_earnout"]

    # Calculate value drivers
    ev_at_entry = result["purchase_price"]
    ev_at_exit = result["exit_enterprise_value"]
    ebitda_growth_value = (result["exit_ebitda"] - base_ebitda) * inputs["exit_ebitda_multiple"]
    multiple_arbitrage = base_ebitda * (inputs["exit_ebitda_multiple"] - inputs["entry_ebitda_multiple"])
    debt_paydown_value = result["debt"] - result["remaining_debt"]

    fig_wf = go.Figure(go.Waterfall(
        name="Equity Value Bridge",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "total"],
        x=["Entry Equity", "EBITDA Growth + Synergies", "Multiple Arbitrage",
           "Debt Paydown", "Add. Equity (Earn-Out)", "Exit Equity"],
        y=[initial_eq, ebitda_growth_value, multiple_arbitrage,
           debt_paydown_value, additional_eq, result["exit_equity"]],
        text=[f"€{v:,.0f}" for v in [initial_eq, ebitda_growth_value,
              multiple_arbitrage, debt_paydown_value, additional_eq, result["exit_equity"]]],
        textposition="outside",
        connector={"line": {"color": "#9CA3AF"}},
        increasing={"marker": {"color": "#10B981"}},
        decreasing={"marker": {"color": "#EF4444"}},
        totals={"marker": {"color": "#3B82F6"}},
    ))
    fig_wf.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        yaxis=dict(title="Equity Value (€)"),
    )
    st.plotly_chart(fig_wf, use_container_width=True)
    st.caption(
        "Drei klassische LBO-Werthebel sichtbar: "
        "**operativer EBITDA-Aufbau** (organic + Synergie), "
        "**Multiple Arbitrage** (Entry vs. Exit), "
        "**Schuldentilgung** (Equity-Anteil wächst mechanisch)."
    )
