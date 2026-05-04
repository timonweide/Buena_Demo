"""
Target Detail — Full Scoring Drill-Down + Editable Weights + Comparison
Tag 4: Volle Implementation der Scoring Engine.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from lib.data_loader import (
    get_active_target,
    get_flag_emoji,
    calculate_derived_metrics,
    load_targets,
)
from lib.pipeline import render_stage_pill
from lib.scoring import (
    compute_full_scores,
    compute_live_flags,
    has_knockouts,
    DEFAULT_WEIGHTS,
    DEFAULT_SUB_WEIGHTS,
)

st.set_page_config(page_title="Target Detail · Buena Piloto", page_icon="📊", layout="wide")
# Auth Gate
if not st.session_state.get("authenticated"):
    st.switch_page("pages/4_👤_Seller_Portal.py")



# ──────────────────────────────────────────────────────────────────────────
# Active Target (defensive)
# ──────────────────────────────────────────────────────────────────────────
target = get_active_target()
if target is None:
    st.error("Keine Targets in der Pipeline. Lege zuerst eines im Seller Portal an.")
    if st.button("→ Seller Portal"):
        st.switch_page("pages/4_👤_Seller_Portal.py")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
with col1:
    st.title(f"📊 {target['name']}")
    st.markdown(
        f"{target['location']}  ·  Stage: {render_stage_pill(target['status'])}  ·  "
        f"Last Update: {target['last_updated']}",
        unsafe_allow_html=True,
    )
with col2:
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("app.py")

# ──────────────────────────────────────────────────────────────────────────
# Editable Weights — Sidebar
# ──────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚖️ Scoring Weights")
    st.caption("Linus kann live priorisieren. Werte werden auto-normalisiert.")

    # Initialize weights in session_state
    if "scoring_weights" not in st.session_state:
        st.session_state["scoring_weights"] = dict(DEFAULT_WEIGHTS)

    weights = st.session_state["scoring_weights"]

    # Top-level weights
    weights["strategic_fit"] = st.slider(
        "Strategic Fit", 0.0, 1.0, weights["strategic_fit"], 0.05, key="w_sf"
    )
    weights["financial_health"] = st.slider(
        "Financial Health", 0.0, 1.0, weights["financial_health"], 0.05, key="w_fh"
    )
    weights["integration_complexity"] = st.slider(
        "Integration Complexity", 0.0, 1.0, weights["integration_complexity"], 0.05,
        key="w_ic"
    )
    weights["synergy_potential"] = st.slider(
        "Synergy Potential", 0.0, 1.0, weights["synergy_potential"], 0.05, key="w_sp"
    )

    weight_sum = sum(weights.values())
    if abs(weight_sum - 1.0) > 0.01:
        st.caption(
            f"Σ = {weight_sum:.2f} — werden auf 1.0 normalisiert"
        )

    if st.button("↻ Reset Weights", use_container_width=True):
        st.session_state["scoring_weights"] = dict(DEFAULT_WEIGHTS)
        st.rerun()


# ──────────────────────────────────────────────────────────────────────────
# Compute Full Scores (with current weights — sub-weights stay at default)
# ──────────────────────────────────────────────────────────────────────────
full = compute_full_scores(target, weights=weights, sub_weights=DEFAULT_SUB_WEIGHTS)
overall = full["overall_score"]
dims = full["dimensions"]

# ──────────────────────────────────────────────────────────────────────────
# Knockouts banner
# ──────────────────────────────────────────────────────────────────────────
ko_active, ko_list = has_knockouts(target)
if ko_active:
    st.error(f"🚫 **AUTO-PAUSE:** Knock-Out triggered — {', '.join(ko_list)}")

# ──────────────────────────────────────────────────────────────────────────
# Score Headline + Spider
# ──────────────────────────────────────────────────────────────────────────
col_score, col_dims = st.columns([1, 3])
with col_score:
    st.metric("Overall Score", f"{overall} / 100")
    if overall >= 70:
        st.success("✅ Strong Fit")
    elif overall >= 50:
        st.warning("⚠️ Borderline")
    else:
        st.error("❌ Pass / Pause")

    # Show overall computation
    with st.expander("Wie ist der Overall-Score berechnet?"):
        weight_sum_top = sum(weights.values()) or 1.0
        for dim_key, dim in dims.items():
            w_norm = weights[dim_key] / weight_sum_top
            contribution = dim["score"] * w_norm
            st.markdown(
                f"**{dim_key.replace('_', ' ').title()}:** "
                f"{dim['score']} × {w_norm:.2f} = **{contribution:.1f}**"
            )

with col_dims:
    dim_keys = ["strategic_fit", "financial_health", "integration_complexity", "synergy_potential"]
    labels = ["Strategic Fit", "Financial Health", "Integration\nComplexity", "Synergy Potential"]
    values = [dims[k]["score"] for k in dim_keys]
    values += values[:1]
    labels_circ = labels + labels[:1]

    fig = go.Figure(
        go.Scatterpolar(r=values, theta=labels_circ, fill="toself", line_color="#3B82F6")
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        height=320,
        margin=dict(l=40, r=40, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ──────────────────────────────────────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────────────────────────────────────
tab_scoring, tab_flags, tab_metrics, tab_pnl, tab_compare, tab_dd = st.tabs([
    "🎯 Score-Breakdown",
    "🏷️ Flags & Risks",
    "📐 Calculated Metrics",
    "💵 Buena Standard P&L (AI)",
    "🔬 Comparison",
    "📋 DD-Antworten",
])

# ────────────────────────────────────────────────────────────────────────
# SCORE BREAKDOWN — voller Drill-Down
# ────────────────────────────────────────────────────────────────────────
with tab_scoring:
    st.subheader("Score-Breakdown — Sub-Scores mit Begründung")
    st.caption(
        "Jeder Sub-Score ist deterministisch aus DD-Antworten berechnet. "
        "Source-Question-IDs sind sichtbar. Gewichte editierbar in der Sidebar."
    )

    dim_meta = {
        "strategic_fit": ("🎯", "Strategic Fit", "#3B82F6"),
        "financial_health": ("💰", "Financial Health", "#10B981"),
        "integration_complexity": ("🔧", "Integration Complexity", "#F59E0B"),
        "synergy_potential": ("⚡", "Synergy Potential", "#A855F7"),
    }

    for dim_key, (icon, dim_name, color) in dim_meta.items():
        dim = dims[dim_key]
        weight_sum_top = sum(weights.values()) or 1.0
        top_weight = weights[dim_key] / weight_sum_top

        st.markdown(
            f"<h4 style='color:{color};margin-top:18px;margin-bottom:4px;'>"
            f"{icon} {dim_name} — {dim['score']}/100"
            f"<span style='font-size:13px;color:#6B7280;font-weight:normal;margin-left:10px;'>"
            f"(Gewicht: {top_weight:.0%})</span>"
            f"</h4>",
            unsafe_allow_html=True,
        )

        # Build sub-score table
        rows = []
        for sub in dim["subscores"]:
            rows.append({
                "Sub-Score": sub["name"],
                "Score": sub["score"],
                "Gewicht": f"{sub['weight']:.0%}",
                "Beitrag": f"{sub['weighted_contribution']:.1f}",
                "Begründung": sub["rationale"],
                "Quelle": sub.get("source_qid", "—"),
            })
        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score", min_value=0, max_value=100, format="%d"
                ),
                "Begründung": st.column_config.TextColumn("Begründung", width="large"),
                "Quelle": st.column_config.TextColumn("DD-Q", width="small"),
            },
        )


# ────────────────────────────────────────────────────────────────────────
# FLAGS
# ────────────────────────────────────────────────────────────────────────
with tab_flags:
    st.subheader("Flags aus DD-Auswertung")
    live_flags = compute_live_flags(target)
    if not live_flags:
        st.info("Keine Flags getriggert.")

    # Sort: red → yellow → green
    severity_order = {"red": 0, "yellow": 1, "green": 2}
    live_flags_sorted = sorted(live_flags, key=lambda f: severity_order.get(f["level"], 3))

    # Section per severity (für klare visuelle Trennung)
    red_flags = [f for f in live_flags_sorted if f["level"] == "red"]
    yellow_flags = [f for f in live_flags_sorted if f["level"] == "yellow"]
    green_flags = [f for f in live_flags_sorted if f["level"] == "green"]

    if red_flags:
        st.markdown(f"##### 🔴 Red Flags ({len(red_flags)})")
        for flag in red_flags:
            st.error(f"🔴 {flag['text']}")
    if yellow_flags:
        st.markdown(f"##### 🟡 Yellow Flags ({len(yellow_flags)})")
        for flag in yellow_flags:
            st.warning(f"🟡 {flag['text']}")
    if green_flags:
        st.markdown(f"##### 🟢 Green Flags ({len(green_flags)})")
        for flag in green_flags:
            st.success(f"🟢 {flag['text']}")

# ────────────────────────────────────────────────────────────────────────
# CALCULATED METRICS
# ────────────────────────────────────────────────────────────────────────
with tab_metrics:
    st.subheader("Auto-berechnete Kennzahlen")
    st.caption(
        "Per Linus' Anmerkung: Was berechnet werden kann, wird nicht abgefragt. "
        "Quell-Felder kommen aus dem Seller Intake."
    )
    m = calculate_derived_metrics(target)
    bench = m["benchmarks"]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Units / Property Manager", f"{m['units_per_pm']:.0f}",
                  delta=f"vs. Buena {bench['units_per_pm_target']}")
        st.metric("Avg. WEG-Größe", f"{m['avg_weg_size']:.0f} Units")
        st.metric("Revenue / Unit / Jahr", f"€{m['revenue_per_unit_year']:,.0f}")
    with c2:
        st.metric("Units / Accounting FTE", f"{m['units_per_accounting']:.0f}")
        st.metric("Units / Total FTE", f"{m['units_per_total_fte']:.0f}")
        st.metric("Revenue / FTE", f"€{m['revenue_per_fte']:,.0f}")
    with c3:
        st.metric("EBITDA-Marge Y1", f"{m['ebitda_margin_y1']:.1f}%")
        st.metric("Revenue CAGR 3J", f"{m['revenue_cagr_3y']:.1f}%")
        st.metric("AR > 90d (% Revenue)", f"{m['ar_over_90d_pct_revenue']:.1f}%")

    st.divider()
    st.markdown("**EBITDA-Marge Trend (3J)**")
    margin_data = pd.DataFrame({
        "Jahr": ["Y3", "Y2", "Y1"],
        "Margin %": [m["ebitda_margin_y3"], m["ebitda_margin_y2"], m["ebitda_margin_y1"]],
    })
    st.line_chart(margin_data, x="Jahr", y="Margin %", height=200)

# ────────────────────────────────────────────────────────────────────────
# P&L (AI-parsed BWA)
# ────────────────────────────────────────────────────────────────────────
with tab_pnl:
    from lib.ai_parser import parse_bwa, aggregate_to_buena_pnl, BUENA_PNL_SCHEMA, all_buena_categories
    import os

    st.subheader("Buena Standard P&L — AI-parsed")
    st.caption(
        "BWA hochladen (Excel oder PDF) → Claude API mappt jede Zeile auf das Buena-Schema. "
        "Mappings mit niedriger Confidence sind manuell editierbar. "
        "Approved P&L wird im LBO Model als alternative Datenquelle angeboten."
    )

    parsed_key = f"ai_pnl_{target['id']}"
    raw_mappings_key = f"ai_mappings_{target['id']}"
    seller_bwa_key = f"bwa_for_target_{target['id']}"

    # ── Mode Indicator + API Key Info ──────────────────────────────────────
    api_active = bool(os.environ.get("ANTHROPIC_API_KEY"))
    
    if api_active:
        st.success("🤖 Claude API aktiv")
    else:
        st.warning("🔧 Mock-Mode aktiv")

    # ── Auto-Import aus Seller Portal ──────────────────────────────────────
    seller_bwa_files = st.session_state.get(seller_bwa_key, [])
    if seller_bwa_files and raw_mappings_key not in st.session_state:
        file_names = [f["name"] for f in seller_bwa_files]
        st.info(
            f"📊 **BWA vom Seller Portal importiert:** {', '.join(file_names)}. "
            f"Klicke 'BWA parsen' um die Analyse zu starten.",
            icon="✅",
        )

    # ── File Upload (manuell, Fallback) ────────────────────────────────────
    uploaded = st.file_uploader(
        "BWA hochladen (Excel oder PDF) — oder vom Seller Portal importiert (siehe oben)",
        type=["xlsx", "xlsm", "pdf"],
        key=f"bwa_upload_{target['id']}",
    )

    # Determine which files to parse (uploaded takes priority over auto-imported)
    files_to_parse = []
    if uploaded:
        uploaded.seek(0)
        files_to_parse = [{"name": uploaded.name, "bytes": uploaded.read()}]
    elif seller_bwa_files:
        files_to_parse = seller_bwa_files

    # ── Parse Buttons ───────────────────────────────────────────────────────
    col_run, col_clear = st.columns([1, 1])
    with col_run:
        parse_label = "🔍 BWA parsen" if not api_active else "🤖 BWA mit Claude parsen"
        if st.button(parse_label, type="primary", use_container_width=True,
                     disabled=(not files_to_parse)):
            all_mappings = []
            for file_info in files_to_parse:
                with st.spinner(f"Parse {file_info['name']}…"):
                    result = parse_bwa(file_info["name"], file_info["bytes"])
                    if result["error"]:
                        st.warning(f"⚠️ {file_info['name']}: {result['error']}")
                    if result["mappings"]:
                        all_mappings.extend(result["mappings"])
            if all_mappings:
                st.session_state[raw_mappings_key] = all_mappings
                st.session_state[f"{parsed_key}_mode"] = result["mode"]
                mode_label = "Claude API" if result["mode"] == "claude" else "Mock"
                st.toast(
                    f"✓ {len(all_mappings)} Zeilen geparst ({mode_label})",
                    icon="🤖",
                )
    with col_clear:
        if st.button("↻ Reset", use_container_width=True):
            for k in [raw_mappings_key, parsed_key, f"{parsed_key}_mode"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()


    mappings = st.session_state.get(raw_mappings_key, [])

    if mappings:
        st.markdown("---")
        st.markdown("**Auto-Mapping-Ergebnisse**")
        st.caption(
            "Mit der Override-Spalte kannst du jedes Mapping manuell korrigieren. "
            "Toggle unten: nur unsichere Mappings anzeigen (Confidence < 70%)."
        )

        # Confidence filter toggle
        col_filter, col_count = st.columns([1, 4])
        with col_filter:
            show_only_low = st.toggle(
                "Nur niedrige Confidence",
                key=f"low_conf_filter_{target['id']}",
                help="Filtert Mappings auf Confidence < 70% — fokussierte Review.",
            )

        # Build editable dataframe (potentially filtered)
        all_cats = all_buena_categories()
        edit_rows = []
        original_indices = []  # Track which mappings index each row corresponds to
        for i, m in enumerate(mappings):
            conf_pct = int(round(m["confidence"] * 100))
            if show_only_low and conf_pct >= 70:
                continue
            edit_rows.append({
                "Konto": m.get("source_konto", ""),
                "Source-Bezeichnung": m["source_label"],
                "Betrag (€)": m["source_amount"],
                "AI-Mapping": m["mapped_to"],
                "Confidence": conf_pct,
                "Override": m.get("override_to", m["mapped_to"]),
                "Begründung": m.get("rationale", ""),
            })
            original_indices.append(i)

        with col_count:
            low_conf_count = sum(1 for m in mappings if int(round(m["confidence"] * 100)) < 70)
            st.caption(
                f"📊 {len(mappings)} Mappings gesamt · "
                f"{low_conf_count} mit Confidence < 70% (manuelle Review empfohlen)"
            )

        if edit_rows:
            edit_df = pd.DataFrame(edit_rows)
            edited = st.data_editor(
                edit_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Betrag (€)": st.column_config.NumberColumn(format="€%.0f"),
                    "Confidence": st.column_config.ProgressColumn(
                        "Conf.", min_value=0, max_value=100, format="%d%%",
                    ),
                    "AI-Mapping": st.column_config.TextColumn("AI-Mapping", disabled=True),
                    "Override": st.column_config.SelectboxColumn(
                        "Override (manuell)",
                        options=all_cats,
                        required=False,
                    ),
                    "Begründung": st.column_config.TextColumn("Rationale", disabled=True, width="medium"),
                },
                num_rows="fixed",
                key=f"editor_{target['id']}_{show_only_low}",
            )

            # Apply overrides back into ORIGINAL mappings index
            for row_idx, row in enumerate(edited.itertuples()):
                orig_idx = original_indices[row_idx]
                mappings[orig_idx]["override_to"] = row.Override
        else:
            st.info("Keine Mappings im aktuellen Filter. Toggle deaktivieren um alle anzuzeigen.")

        st.markdown("---")
        col_aggr, col_save = st.columns([3, 1])
        with col_aggr:
            agg = aggregate_to_buena_pnl(mappings)
            st.markdown("### Aggregiertes Buena Standard P&L")

            # ════════════════════════════════════════════════════════════
            # P&L im Standard-GuV-Format mit Subtotals + Margen
            # ════════════════════════════════════════════════════════════
            subt = agg["subtotals"]
            structured = agg["structured"]
            revenue_total = subt["Revenue Total"]

            def margin_pct(numerator):
                return (numerator / revenue_total * 100) if revenue_total > 0 else 0

            def fmt_eur(val):
                if val == 0:
                    return "—"
                return f"€{val:,.0f}".replace(",", ".")

            def fmt_pct(val):
                return f"{val:.1f}%"

            # Subtotals + dazugehörige Detail-Buckets
            # Reihenfolge: Revenue → Direct Costs (= COGS) → Gross Profit
            #   → Operating Expenses → EBITDA → D&A → EBIT → Financial → EBT → Tax → Net Income

            # Revenue Bucket
            with st.container():
                col_label, col_eur, col_margin = st.columns([4, 2, 1])
                col_label.markdown("**Revenue**")
                col_eur.markdown(f"**{fmt_eur(revenue_total)}**")
                col_margin.markdown("**100.0%**")
            with st.expander("Details Revenue", expanded=False):
                rev_df = pd.DataFrame(
                    [
                        {"Position": item, "Betrag": fmt_eur(val), "% Revenue": fmt_pct(margin_pct(val))}
                        for item, val in structured["Revenue"].items() if val != 0
                    ] or [{"Position": "—", "Betrag": "—", "% Revenue": "—"}]
                )
                st.dataframe(rev_df, hide_index=True, use_container_width=True)

            # Direct Costs (COGS-Equivalent)
            direct_costs = sum(structured["Direct Costs"].values())
            with st.container():
                col_label, col_eur, col_margin = st.columns([4, 2, 1])
                col_label.markdown("Direct Costs (Personnel)")
                col_eur.markdown(fmt_eur(direct_costs))
                col_margin.markdown(fmt_pct(margin_pct(direct_costs)))
            with st.expander("Details Direct Costs", expanded=False):
                dc_df = pd.DataFrame(
                    [
                        {"Position": item, "Betrag": fmt_eur(val), "% Revenue": fmt_pct(margin_pct(val))}
                        for item, val in structured["Direct Costs"].items() if val != 0
                    ] or [{"Position": "—", "Betrag": "—", "% Revenue": "—"}]
                )
                st.dataframe(dc_df, hide_index=True, use_container_width=True)

            # Gross Profit Subtotal
            gp = subt["Gross Profit"]
            st.markdown(
                f"<div style='border-top:1px solid #6B7280;padding-top:6px;margin-top:4px;"
                f"display:flex;justify-content:space-between;font-weight:700;color:#1D4ED8;'>"
                f"<span>Gross Profit</span><span>{fmt_eur(gp)}  ·  {fmt_pct(margin_pct(gp))}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("&nbsp;", unsafe_allow_html=True)

            # Operating Expenses
            opex = sum(structured["Operating Expenses"].values())
            with st.container():
                col_label, col_eur, col_margin = st.columns([4, 2, 1])
                col_label.markdown("Operating Expenses")
                col_eur.markdown(fmt_eur(opex))
                col_margin.markdown(fmt_pct(margin_pct(opex)))
            with st.expander("Details Operating Expenses", expanded=False):
                opex_df = pd.DataFrame(
                    [
                        {"Position": item, "Betrag": fmt_eur(val), "% Revenue": fmt_pct(margin_pct(val))}
                        for item, val in structured["Operating Expenses"].items() if val != 0
                    ] or [{"Position": "—", "Betrag": "—", "% Revenue": "—"}]
                )
                st.dataframe(opex_df, hide_index=True, use_container_width=True)

            # EBITDA Subtotal
            ebitda = subt["EBITDA"]
            st.markdown(
                f"<div style='border-top:2px solid #1D4ED8;padding-top:8px;margin-top:6px;"
                f"display:flex;justify-content:space-between;font-weight:700;color:#1D4ED8;font-size:16px;'>"
                f"<span>EBITDA</span><span>{fmt_eur(ebitda)}  ·  {fmt_pct(margin_pct(ebitda))}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("&nbsp;", unsafe_allow_html=True)

            # D&A
            da = sum(structured["D&A"].values())
            with st.container():
                col_label, col_eur, col_margin = st.columns([4, 2, 1])
                col_label.markdown("D&A (Abschreibungen)")
                col_eur.markdown(fmt_eur(da))
                col_margin.markdown(fmt_pct(margin_pct(da)))
            with st.expander("Details D&A", expanded=False):
                da_df = pd.DataFrame(
                    [
                        {"Position": item, "Betrag": fmt_eur(val), "% Revenue": fmt_pct(margin_pct(val))}
                        for item, val in structured["D&A"].items() if val != 0
                    ] or [{"Position": "—", "Betrag": "—", "% Revenue": "—"}]
                )
                st.dataframe(da_df, hide_index=True, use_container_width=True)

            # EBIT
            ebit = subt["EBIT"]
            st.markdown(
                f"<div style='border-top:1px solid #6B7280;padding-top:6px;margin-top:4px;"
                f"display:flex;justify-content:space-between;font-weight:700;color:#1D4ED8;'>"
                f"<span>EBIT</span><span>{fmt_eur(ebit)}  ·  {fmt_pct(margin_pct(ebit))}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("&nbsp;", unsafe_allow_html=True)

            # Financial Result
            fin = sum(structured["Financial"].values())
            with st.container():
                col_label, col_eur, col_margin = st.columns([4, 2, 1])
                col_label.markdown("Financial Result")
                col_eur.markdown(fmt_eur(fin))
                col_margin.markdown(fmt_pct(margin_pct(fin)))
            with st.expander("Details Financial Result", expanded=False):
                fin_df = pd.DataFrame(
                    [
                        {"Position": item, "Betrag": fmt_eur(val), "% Revenue": fmt_pct(margin_pct(val))}
                        for item, val in structured["Financial"].items() if val != 0
                    ] or [{"Position": "—", "Betrag": "—", "% Revenue": "—"}]
                )
                st.dataframe(fin_df, hide_index=True, use_container_width=True)

            # EBT
            ebt = subt["EBT"]
            st.markdown(
                f"<div style='border-top:1px solid #6B7280;padding-top:6px;margin-top:4px;"
                f"display:flex;justify-content:space-between;font-weight:700;color:#1D4ED8;'>"
                f"<span>EBT (Pre-Tax Income)</span><span>{fmt_eur(ebt)}  ·  {fmt_pct(margin_pct(ebt))}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("&nbsp;", unsafe_allow_html=True)

            # Tax
            tax = sum(structured["Tax"].values())
            with st.container():
                col_label, col_eur, col_margin = st.columns([4, 2, 1])
                col_label.markdown("Tax")
                col_eur.markdown(fmt_eur(tax))
                col_margin.markdown(fmt_pct(margin_pct(tax)))
            with st.expander("Details Tax", expanded=False):
                tax_df = pd.DataFrame(
                    [
                        {"Position": item, "Betrag": fmt_eur(val), "% Revenue": fmt_pct(margin_pct(val))}
                        for item, val in structured["Tax"].items() if val != 0
                    ] or [{"Position": "—", "Betrag": "—", "% Revenue": "—"}]
                )
                st.dataframe(tax_df, hide_index=True, use_container_width=True)

            # Net Income (final)
            ni = subt["Net Income"]
            st.markdown(
                f"<div style='border-top:2px solid #10B981;padding-top:8px;margin-top:6px;"
                f"display:flex;justify-content:space-between;font-weight:700;color:#10B981;font-size:16px;'>"
                f"<span>Net Income</span><span>{fmt_eur(ni)}  ·  {fmt_pct(margin_pct(ni))}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Comparison vs. self-reported
            self_rev = target["financials"].get("revenue_y1", 0) or 0
            self_eb = target["financials"].get("ebitda_y1", 0) or 0
            self_margin = (self_eb / self_rev * 100) if self_rev > 0 else 0
            parsed_eb = agg["subtotals"]["EBITDA"]
            parsed_rev = agg["subtotals"]["Revenue Total"]

            st.markdown("&nbsp;", unsafe_allow_html=True)
            with st.expander("📊 Vergleich: Self-reported (DD) vs. AI-parsed BWA"):
                cmp_df = pd.DataFrame({
                    "Metrik": ["Revenue", "EBITDA", "EBITDA-Marge"],
                    "Self-reported (DD)": [
                        f"€{self_rev:,.0f}",
                        f"€{self_eb:,.0f}",
                        f"{self_margin:.1f}%",
                    ],
                    "AI-parsed (BWA)": [
                        f"€{parsed_rev:,.0f}",
                        f"€{parsed_eb:,.0f}",
                        f"{agg['ebitda_margin_pct']:.1f}%",
                    ],
                    "Δ": [
                        f"€{parsed_rev - self_rev:+,.0f}",
                        f"€{parsed_eb - self_eb:+,.0f}",
                        f"{agg['ebitda_margin_pct'] - self_margin:+.1f}pp",
                    ],
                })
                st.dataframe(cmp_df, hide_index=True, use_container_width=True)
                if self_eb > 0 and abs(parsed_eb - self_eb) > self_eb * 0.2:
                    st.warning(
                        "⚠️ Significante Abweichung zwischen Self-reported DD und BWA — "
                        "DD-Daten sollten auf Basis der BWA überarbeitet werden."
                    )

        with col_save:
            st.markdown("### Approve")
            st.caption(
                "Approved P&L wird im LBO Model als Datenquelle angeboten."
            )
            if st.button("✅ P&L approven & für LBO nutzen",
                         type="primary", use_container_width=True):
                st.session_state[parsed_key] = agg
                st.toast("✓ P&L approved — verfügbar im LBO Model", icon="✅")

            if parsed_key in st.session_state:
                st.success("✅ Approved")
                if st.button("Unapprove", use_container_width=True):
                    del st.session_state[parsed_key]
                    st.rerun()
    else:
        st.info(
            "💡 Lade eine BWA hoch und klicke 'BWA parsen'. "
            "Eine Demo-BWA findest du unter `data/demo_files/demo_bwa_mueller.xlsx`."
        )

# ────────────────────────────────────────────────────────────────────────
# COMPARISON — Side-by-Side
# ────────────────────────────────────────────────────────────────────────
with tab_compare:
    st.subheader("🔬 Side-by-Side Vergleich")
    st.caption(
        "Vergleiche das aktive Target mit anderen Targets in der Pipeline. "
        "Gleiche Gewichte werden auf alle angewandt."
    )

    all_targets = load_targets()
    other_options = {t["id"]: t["name"] for t in all_targets if t["id"] != target["id"]}

    if not other_options:
        st.info("Nur 1 Target in der Pipeline — Vergleich braucht mindestens 2.")
    else:
        compare_ids = st.multiselect(
            "Mit welchen Targets vergleichen?",
            options=list(other_options.keys()),
            default=list(other_options.keys())[: min(2, len(other_options))],
            format_func=lambda tid: other_options[tid],
        )

        if compare_ids:
            compare_targets = [target] + [
                next(t for t in all_targets if t["id"] == tid)
                for tid in compare_ids
            ]

            # Spider Chart Overlay
            fig = go.Figure()
            colors = ["#3B82F6", "#F59E0B", "#10B981", "#A855F7", "#EF4444"]
            spider_labels = [
                "Strategic Fit", "Financial Health",
                "Integration\nComplexity", "Synergy Potential",
            ]
            for i, t in enumerate(compare_targets):
                t_full = compute_full_scores(t, weights=weights, sub_weights=DEFAULT_SUB_WEIGHTS)
                t_dims = t_full["dimensions"]
                vals = [
                    t_dims["strategic_fit"]["score"],
                    t_dims["financial_health"]["score"],
                    t_dims["integration_complexity"]["score"],
                    t_dims["synergy_potential"]["score"],
                ]
                vals += vals[:1]
                fig.add_trace(go.Scatterpolar(
                    r=vals,
                    theta=spider_labels + spider_labels[:1],
                    fill="toself",
                    name=t["name"],
                    line_color=colors[i % len(colors)],
                    opacity=0.5,
                ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                height=420,
                margin=dict(l=40, r=40, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Metric Comparison Table
            st.divider()
            st.markdown("**Detaillierter Vergleich**")
            rows = []
            for t in compare_targets:
                t_full = compute_full_scores(t, weights=weights, sub_weights=DEFAULT_SUB_WEIGHTS)
                t_metrics = calculate_derived_metrics(t)
                rows.append({
                    "Target": t["name"],
                    "Stage": t["status"],
                    "Overall Score": t_full["overall_score"],
                    "Units": t["portfolio"]["units_total"],
                    "Revenue (Y1)": f"€{t['financials']['revenue_y1']:,.0f}",
                    "EBITDA-Marge": f"{t_metrics['ebitda_margin_y1']:.1f}%",
                    "Strategic Fit": t_full["dimensions"]["strategic_fit"]["score"],
                    "Financial": t_full["dimensions"]["financial_health"]["score"],
                    "Integration": t_full["dimensions"]["integration_complexity"]["score"],
                    "Synergy": t_full["dimensions"]["synergy_potential"]["score"],
                })
            cmp_df = pd.DataFrame(rows)
            st.dataframe(
                cmp_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Overall Score": st.column_config.ProgressColumn(
                        "Overall", min_value=0, max_value=100, format="%d"
                    ),
                    "Strategic Fit": st.column_config.NumberColumn(format="%d"),
                    "Financial": st.column_config.NumberColumn(format="%d"),
                    "Integration": st.column_config.NumberColumn(format="%d"),
                    "Synergy": st.column_config.NumberColumn(format="%d"),
                },
            )

# ────────────────────────────────────────────────────────────────────────
# DD ANSWERS — Schema-aware view (Frage + Antwort)
# ────────────────────────────────────────────────────────────────────────
with tab_dd:
    from lib.data_loader import load_dd_schema
    from lib.form_engine import QUESTION_TO_TARGET_PATH

    st.subheader("DD-Antworten")
    st.caption(
        "Antworten aus dem Seller Intake. Schema-aware View — pro Frage die Antwort, "
        "gruppiert nach Sektion."
    )

    dd_schema = load_dd_schema()

    def get_answer_from_target(qid: str, target: dict):
        """Liest die Antwort für eine DD-Frage aus den Target-Daten."""
        path = QUESTION_TO_TARGET_PATH.get(qid)
        if not path:
            return None
        cur = target
        for p in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(p)
            if cur is None:
                return None
        return cur

    def format_answer(val, qtype: str = None):
        """Hübsche Darstellung für verschiedene Datentypen."""
        if val is None:
            return "—"
        if isinstance(val, bool):
            return "✓ Ja" if val else "✗ Nein"
        if isinstance(val, (int, float)):
            # Heuristic: large numbers = currency or counts
            if isinstance(val, float) and val != int(val):
                return f"{val:,.1f}".replace(",", ".")
            return f"{int(val):,}".replace(",", ".")
        if isinstance(val, list):
            return ", ".join(str(v) for v in val) if val else "—"
        return str(val)

    # Render per category
    for cat in dd_schema["categories"]:
        cat_questions = cat["questions"]
        # Count answered questions
        answered = 0
        for q in cat_questions:
            val = get_answer_from_target(q["id"], target)
            if val is not None:
                answered += 1

        with st.expander(
            f"{cat['icon']} {cat['name']}  ·  {answered}/{len(cat_questions)} beantwortet",
            expanded=False,
        ):
            rows = []
            for q in cat_questions:
                val = get_answer_from_target(q["id"], target)
                rows.append({
                    "ID": q["id"],
                    "Frage": q["text"],
                    "Antwort": format_answer(val, q.get("type")),
                })
            df_dd = pd.DataFrame(rows)
            st.dataframe(
                df_dd,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="small"),
                    "Frage": st.column_config.TextColumn("Frage", width="large"),
                    "Antwort": st.column_config.TextColumn("Antwort", width="medium"),
                },
            )
