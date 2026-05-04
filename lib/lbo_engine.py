"""
Buena Piloto — LBO Engine (Voll-Implementierung)
- Year-by-Year P&L Projection mit Synergie-Phasen (Y1, Y2, Run-Rate ab Y3)
- FCF-Berechnung (EBITDA → EBIT → NOPAT → +D&A − CapEx − ΔNWC)
- Debt Schedule (Beginning → Mandatory Amort → Interest → Cash Sweep → Ending)
- Earn-Out Trigger Logic (zahlt nur bei EBITDA-Threshold)
- Exit Calculation + IRR/MoM
- Long Holding Period (3-20 Jahre, Buena hält langfristig)
"""

DEFAULT_LBO_INPUTS = {
    # Deal-Struktur
    "entry_ebitda_multiple": 5.0,
    "debt_pct": 50.0,
    "interest_rate_pct": 7.0,
    "mandatory_amortization_pct": 10.0,
    "tax_rate_pct": 30.0,

    # Holding & Exit (3-20J — Buena hält langfristig)
    "holding_period_years": 5,
    "exit_ebitda_multiple": 6.0,

    # Operating Case
    "ebitda_growth_pct": 8.0,
    "synergy_y1": 0,
    "synergy_y2": 0,
    "synergy_run_rate": 0,

    # Free Cash Flow Assumptions (defaults für Property-Mgmt)
    "da_pct_revenue": 1.5,         # D&A als % vom Revenue (asset-light)
    "capex_pct_revenue": 1.0,      # CapEx (Software, Office)
    "nwc_change_pct_revenue": 0.5, # NWC-Aufbau bei Wachstum
    "revenue_growth_pct": 5.0,     # Top-line Growth (kann anders sein als EBITDA-Growth durch Margin Expansion)

    # Earn-Out (Mittelstand-typisch)
    "earnout_amount": 0,
    "earnout_year": 2,
    "earnout_threshold_ebitda": 0,
    "earnout_paid_from_fcf": True,
}


def calculate_lbo(inputs: dict, base_ebitda: float, base_revenue: float = None) -> dict:
    """
    Volle LBO-Berechnung. Liefert komplette Year-by-Year Projection.

    Returns:
        {
            "purchase_price": float,
            "debt": float,
            "equity": float,
            "yearly_data": [
                {year, revenue, ebitda_organic, synergy, ebitda, da, ebit, taxes,
                 nopat, capex, nwc_change, fcf_pre_earnout, earnout_paid,
                 fcf_post_earnout, beginning_debt, mandatory_amort,
                 interest_expense, cash_sweep, ending_debt}
            ],
            "exit_year": int,
            "exit_ebitda": float,
            "exit_enterprise_value": float,
            "remaining_debt": float,
            "exit_equity": float,
            "additional_equity_for_earnout": float,
            "total_equity_invested": float,
            "mom": float,
            "irr_pct": float,
            "earnout_summary": {triggered, year, amount}
        }
    """
    # ─── Sources & Uses ───
    purchase_price = base_ebitda * inputs["entry_ebitda_multiple"]
    debt = purchase_price * inputs["debt_pct"] / 100
    equity = purchase_price - debt

    # If no revenue given, infer from typical PMC margin (10%)
    if base_revenue is None or base_revenue <= 0:
        base_revenue = base_ebitda / 0.10 if base_ebitda > 0 else 1_000_000

    # ─── Year-by-Year Modeling ───
    holding = int(inputs["holding_period_years"])
    rate_growth_eb = inputs["ebitda_growth_pct"] / 100
    rate_growth_rev = inputs["revenue_growth_pct"] / 100
    tax = inputs["tax_rate_pct"] / 100
    int_rate = inputs["interest_rate_pct"] / 100
    mand_amort_pct = inputs["mandatory_amortization_pct"] / 100

    da_pct = inputs["da_pct_revenue"] / 100
    capex_pct = inputs["capex_pct_revenue"] / 100
    nwc_pct = inputs["nwc_change_pct_revenue"] / 100

    earnout_amt = inputs["earnout_amount"]
    earnout_yr = inputs["earnout_year"]
    earnout_thr = inputs["earnout_threshold_ebitda"]
    earnout_from_fcf = inputs["earnout_paid_from_fcf"]

    yearly_data = []
    current_debt = debt
    additional_equity = 0  # if earn-out funded by new equity injection
    earnout_triggered = False
    earnout_year_actual = None

    for year in range(1, holding + 1):
        # Revenue: grows organic
        revenue = base_revenue * ((1 + rate_growth_rev) ** year)

        # EBITDA: organic + synergies
        ebitda_organic = base_ebitda * ((1 + rate_growth_eb) ** year)
        if year == 1:
            synergy = inputs["synergy_y1"]
        elif year == 2:
            synergy = inputs["synergy_y2"]
        else:
            synergy = inputs["synergy_run_rate"]
        ebitda_total = ebitda_organic + synergy

        # P&L Walk
        da = revenue * da_pct
        ebit = ebitda_total - da

        # Interest on AVERAGE debt this year (simplification: on beginning balance)
        interest_expense = current_debt * int_rate

        # EBT and taxes
        ebt = ebit - interest_expense
        taxes = max(0, ebt * tax)
        net_income = ebt - taxes

        # FCF: NI + D&A - CapEx - ΔNWC (and add back interest? No - levered FCF for debt paydown)
        capex = revenue * capex_pct
        prev_revenue = base_revenue if year == 1 else (base_revenue * ((1 + rate_growth_rev) ** (year - 1)))
        nwc_change = (revenue - prev_revenue) * nwc_pct

        fcf_pre_earnout = net_income + da - capex - nwc_change

        # Earn-Out Trigger
        earnout_paid = 0
        if earnout_amt > 0 and year == earnout_yr and not earnout_triggered:
            if ebitda_total >= earnout_thr:
                earnout_paid = earnout_amt
                earnout_triggered = True
                earnout_year_actual = year
                if not earnout_from_fcf:
                    additional_equity += earnout_amt

        fcf_post_earnout = fcf_pre_earnout
        if earnout_from_fcf:
            fcf_post_earnout = fcf_pre_earnout - earnout_paid

        # Debt Schedule
        beginning_debt = current_debt
        mandatory_amort = min(beginning_debt, beginning_debt * mand_amort_pct)
        cash_after_mandatory = max(0, fcf_post_earnout - mandatory_amort)
        cash_sweep = min(beginning_debt - mandatory_amort, cash_after_mandatory)
        ending_debt = max(0, beginning_debt - mandatory_amort - cash_sweep)

        yearly_data.append({
            "year": year,
            "revenue": revenue,
            "ebitda_organic": ebitda_organic,
            "synergy": synergy,
            "ebitda": ebitda_total,
            "da": da,
            "ebit": ebit,
            "interest_expense": interest_expense,
            "ebt": ebt,
            "taxes": taxes,
            "net_income": net_income,
            "capex": capex,
            "nwc_change": nwc_change,
            "fcf_pre_earnout": fcf_pre_earnout,
            "earnout_paid": earnout_paid,
            "fcf_post_earnout": fcf_post_earnout,
            "beginning_debt": beginning_debt,
            "mandatory_amort": mandatory_amort,
            "cash_sweep": cash_sweep,
            "ending_debt": ending_debt,
        })

        current_debt = ending_debt

    # ─── Exit ───
    exit_ebitda = yearly_data[-1]["ebitda"]
    exit_enterprise_value = exit_ebitda * inputs["exit_ebitda_multiple"]
    remaining_debt = yearly_data[-1]["ending_debt"]
    exit_equity = exit_enterprise_value - remaining_debt

    # ─── Returns ───
    total_equity_invested = equity + additional_equity
    if total_equity_invested > 0 and exit_equity > 0:
        mom = exit_equity / total_equity_invested
        # Approx IRR: assumes single in/out, ignores timing of additional equity (Tag 6 könnte das verfeinern)
        irr_pct = (mom ** (1 / holding) - 1) * 100
    else:
        mom = 0
        irr_pct = 0

    return {
        "purchase_price": purchase_price,
        "debt": debt,
        "equity": equity,
        "additional_equity_for_earnout": additional_equity,
        "total_equity_invested": total_equity_invested,
        "yearly_data": yearly_data,
        "exit_year": holding,
        "exit_ebitda": exit_ebitda,
        "exit_enterprise_value": exit_enterprise_value,
        "remaining_debt": remaining_debt,
        "exit_equity": exit_equity,
        "mom": mom,
        "irr_pct": irr_pct,
        "earnout_summary": {
            "triggered": earnout_triggered,
            "year": earnout_year_actual,
            "amount": earnout_amt if earnout_triggered else 0,
            "threshold": earnout_thr,
            "funded_from": "FCF" if earnout_from_fcf else "New Equity",
        },
    }
