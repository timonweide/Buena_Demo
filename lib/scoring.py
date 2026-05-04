"""
Buena Piloto — Full Scoring Engine
Berechnet 4 Dimensionen, jede aus 3-4 Sub-Komponenten.
Jeder Score-Punkt ist zu einer DD-Antwort traceable.

Output-Struktur pro Dimension:
{
    "score": int 0-100,
    "subscores": [
        {
            "name": str,
            "score": int 0-100,
            "weight": float,
            "weighted_contribution": float,
            "rationale": str,        # human-readable explanation
            "source_qid": str | None  # which DD question drove this
        }
    ]
}
"""
from typing import Any


# ──────────────────────────────────────────────────────────────────────────
# Default Weights — können vom User im Admin-Panel überschrieben werden
# ──────────────────────────────────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    "strategic_fit": 0.25,
    "financial_health": 0.30,
    "integration_complexity": 0.25,
    "synergy_potential": 0.20,
}

DEFAULT_SUB_WEIGHTS = {
    "strategic_fit": {
        "size_fit": 0.40,
        "succession_trigger": 0.30,
        "transition_runway": 0.30,
    },
    "financial_health": {
        "ebitda_margin": 0.40,
        "revenue_growth": 0.25,
        "working_capital_quality": 0.20,
        "trustee_compliance": 0.15,
    },
    "integration_complexity": {
        "software_migration": 0.35,
        "customer_concentration": 0.25,
        "personnel_stability": 0.20,
        "ownership_complexity": 0.20,
    },
    "synergy_potential": {
        "cross_sell_base": 0.35,
        "backoffice_consolidation": 0.30,
        "ai_automation_gap": 0.20,
        "pricing_lever": 0.15,
    },
}


# ──────────────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────────────
def _clamp(x: float) -> int:
    return max(0, min(100, int(round(x))))


def _safe_get(d: dict, *keys, default=None):
    """Nested dict access mit Default."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


# ──────────────────────────────────────────────────────────────────────────
# STRATEGIC FIT — Sub-Scores
# ──────────────────────────────────────────────────────────────────────────
def _strategic_size_fit(target: dict) -> dict:
    """Sweet Spot 1.500-8.000 Units = volle Punktzahl. Außerhalb: linear abnehmend."""
    units = _safe_get(target, "portfolio", "units_total", default=0) or 0

    if 1500 <= units <= 8000:
        score = 100
        rat = f"{units:,} Units im Buena Sweet Spot (1.500–8.000)"
    elif 800 <= units < 1500:
        # 800 → 50, 1500 → 100
        score = int(50 + (units - 800) / 700 * 50)
        rat = f"{units:,} Units knapp unter Sweet Spot — Synergiehebel limitiert"
    elif 8000 < units <= 15000:
        # 8000 → 100, 15000 → 60
        score = int(100 - (units - 8000) / 7000 * 40)
        rat = f"{units:,} Units über Sweet Spot — Integrations-Team-Capacity beachten"
    elif units < 800:
        score = int(units / 800 * 50) if units > 0 else 0
        rat = f"{units:,} Units zu klein — Akquisitions-Overhead nicht gerechtfertigt"
    else:  # > 15000
        score = max(20, 60 - int((units - 15000) / 1000 * 5))
        rat = f"{units:,} Units sehr groß — alternative Deal-Struktur nötig"

    return {
        "name": "Size Fit",
        "score": _clamp(score),
        "rationale": rat,
        "source_qid": "2.1",
    }


def _strategic_succession_trigger(target: dict) -> dict:
    """Owner-Age + Sale-Motivation = Nachfolge-Indicator."""
    owner_age = _safe_get(target, "company_basics", "owner_age", default=0) or 0
    motivation = _safe_get(target, "company_basics", "sale_motivation", default="")

    score = 50
    parts = []

    if owner_age >= 65:
        score += 30
        parts.append(f"Inhaber {owner_age}J (klarer Nachfolge-Trigger)")
    elif owner_age >= 60:
        score += 20
        parts.append(f"Inhaber {owner_age}J (Nachfolge wahrscheinlich)")
    elif owner_age >= 55:
        score += 5
        parts.append(f"Inhaber {owner_age}J")
    elif owner_age > 0:
        parts.append(f"Inhaber {owner_age}J — kein Nachfolge-Trigger")

    if motivation == "Nachfolge":
        score += 20
        parts.append("Verkaufsmotivation: Nachfolge")
    elif motivation == "Strategischer Exit":
        score += 5
        parts.append("Verkaufsmotivation: Strategischer Exit")
    elif motivation == "Finanzielle Notlage":
        score -= 10
        parts.append("Verkaufsmotivation: Notlage — DD-Tiefe erhöhen")

    return {
        "name": "Succession Trigger",
        "score": _clamp(score),
        "rationale": " · ".join(parts) if parts else "Keine ausreichenden Daten",
        "source_qid": "1.8 + 1.9",
    }


def _strategic_transition_runway(target: dict) -> dict:
    """Übergangsperiode = wie viel Knowledge-Transfer Zeit haben wir."""
    period = _safe_get(target, "company_basics", "transition_period", default="")

    mapping = {
        "<3 Monate": (15, "Sehr kurze Übergangsphase — hohes Knowledge-Transfer-Risiko"),
        "3-12 Monate": (70, "Solide Übergangsphase"),
        "12-24 Monate": (95, "Lange Übergangsphase ideal für Wissenstransfer"),
        "> 24 Monate": (90, "Sehr lange Übergangsphase — Bindungsstruktur klären"),
    }

    if period in mapping:
        score, rat = mapping[period]
    else:
        score, rat = 50, "Übergangsphase nicht spezifiziert"

    return {
        "name": "Transition Runway",
        "score": _clamp(score),
        "rationale": rat,
        "source_qid": "1.10",
    }


# ──────────────────────────────────────────────────────────────────────────
# FINANCIAL HEALTH — Sub-Scores
# ──────────────────────────────────────────────────────────────────────────
def _financial_ebitda_margin(target: dict) -> dict:
    """EBITDA-Marge Y1, kalibriert auf Property-Mgmt-Branche."""
    rev = _safe_get(target, "financials", "revenue_y1", default=1) or 1
    ebitda = _safe_get(target, "financials", "ebitda_y1", default=0) or 0
    margin = (ebitda / rev) * 100 if rev > 0 else 0

    if margin >= 18:
        score = 100
        rat = f"EBITDA-Marge {margin:.1f}% — sehr stark, deutlich über Buena-Mittel"
    elif margin >= 12:
        score = 80
        rat = f"EBITDA-Marge {margin:.1f}% — solide, gesunder Operating-Hebel"
    elif margin >= 7:
        score = 55
        rat = f"EBITDA-Marge {margin:.1f}% — durchschnittlich, Optimierungspotenzial"
    elif margin >= 3:
        score = 30
        rat = f"EBITDA-Marge {margin:.1f}% — niedrig, signifikante Margenarbeit nötig"
    else:
        score = 10
        rat = f"EBITDA-Marge {margin:.1f}% — Verlust- oder Niedrigmargen-Profil"

    return {
        "name": "EBITDA-Marge",
        "score": _clamp(score),
        "rationale": rat,
        "source_qid": "6.1 / 6.4",
    }


def _financial_revenue_growth(target: dict) -> dict:
    """3-Jahres CAGR."""
    rev_y1 = _safe_get(target, "financials", "revenue_y1", default=1) or 1
    rev_y3 = _safe_get(target, "financials", "revenue_y3", default=1) or 1

    if rev_y3 <= 0:
        return {
            "name": "Revenue Growth",
            "score": 50,
            "rationale": "Keine Daten für 3-Jahres-Vergleich",
            "source_qid": "6.1 / 6.3",
        }

    cagr = ((rev_y1 / rev_y3) ** 0.5 - 1) * 100

    if cagr >= 12:
        score = 100
        rat = f"3J-CAGR {cagr:.1f}% — starkes organisches Wachstum"
    elif cagr >= 6:
        score = 75
        rat = f"3J-CAGR {cagr:.1f}% — solides Wachstum"
    elif cagr >= 0:
        score = 50
        rat = f"3J-CAGR {cagr:.1f}% — flach, organisches Add-on-Potenzial wichtig"
    elif cagr >= -5:
        score = 25
        rat = f"3J-CAGR {cagr:.1f}% — Schrumpfung, Ursache klären"
    else:
        score = 10
        rat = f"3J-CAGR {cagr:.1f}% — starke Schrumpfung, Red Flag"

    return {
        "name": "Revenue Growth",
        "score": _clamp(score),
        "rationale": rat,
        "source_qid": "6.1 / 6.3",
    }


def _financial_working_capital(target: dict) -> dict:
    """AR > 90 Tage als % vom Umsatz."""
    rev = _safe_get(target, "financials", "revenue_y1", default=1) or 1
    ar_90 = _safe_get(target, "financials", "ar_over_90d", default=0) or 0
    pct = (ar_90 / rev) * 100 if rev > 0 else 0

    if pct < 1:
        score = 100
        rat = f"AR > 90d nur {pct:.1f}% vom Umsatz — sehr saubere WC-Struktur"
    elif pct < 3:
        score = 80
        rat = f"AR > 90d {pct:.1f}% vom Umsatz — gesund"
    elif pct < 6:
        score = 50
        rat = f"AR > 90d {pct:.1f}% vom Umsatz — Mahnwesen-Aufmerksamkeit"
    elif pct < 10:
        score = 25
        rat = f"AR > 90d {pct:.1f}% vom Umsatz — WC-Risiko, Cash Conversion verbessern"
    else:
        score = 10
        rat = f"AR > 90d {pct:.1f}% vom Umsatz — kritisch hoch"

    return {
        "name": "Working Capital Quality",
        "score": _clamp(score),
        "rationale": rat,
        "source_qid": "6.8",
    }


def _financial_trustee_compliance(target: dict) -> dict:
    """Treuhand-Mittel Compliance + steuerliche Sauberkeit."""
    trustee_loss = _safe_get(target, "knockouts", "trustee_loss", default=False)
    tax_proc = _safe_get(target, "financials", "tax_proceedings", default=False)
    has_funds = _safe_get(target, "financials", "trustee_funds", default=0) or 0

    score = 100
    parts = []

    if trustee_loss:
        score = 0
        parts.append("Treuhand-Verlust historisch gemeldet — KO")
    elif has_funds > 0:
        parts.append(f"€{has_funds:,.0f} Treuhand-Mittel verwaltet, keine Verluste")

    if tax_proc:
        score -= 30
        parts.append("Laufende Steuerprüfung")

    return {
        "name": "Trustee & Tax Compliance",
        "score": _clamp(score),
        "rationale": " · ".join(parts) if parts else "Compliance-Status unklar",
        "source_qid": "6.10 / 6.11",
    }


# ──────────────────────────────────────────────────────────────────────────
# INTEGRATION COMPLEXITY — Sub-Scores (höher = WENIGER komplex)
# ──────────────────────────────────────────────────────────────────────────
def _integration_software(target: dict) -> dict:
    """Software-Stack-Migration — Excel/Word ist Albtraum, Domus ist trivial."""
    sw = _safe_get(target, "operations", "primary_software", default="")
    deployment = _safe_get(target, "operations", "deployment", default="")

    sw_score_map = {
        "Domus": 90,
        "Wodis Sigma": 85,
        "immoware24": 90,
        "Karthago": 60,
        "Hausperle": 70,
        "Stratis": 65,
        "Eigenbau": 30,
        "Excel/Word": 5,
        "Sonstige": 50,
    }
    base = sw_score_map.get(sw, 50)

    deploy_adj = 0
    if deployment == "Cloud":
        deploy_adj = 10
    elif deployment == "On-Prem":
        deploy_adj = -15
    elif deployment == "Hybrid":
        deploy_adj = -5

    score = base + deploy_adj

    rat = f"Software: {sw or '?'} ({deployment or '?'})"
    if sw == "Excel/Word":
        rat += " — Re-Implementierung von Grund auf, nicht Migration"
    elif sw == "Eigenbau":
        rat += " — Custom-Mapping aufwendig"
    elif base >= 80:
        rat += " — Standard-Migration via etabliertem Connector möglich"

    return {
        "name": "Software Migration",
        "score": _clamp(score),
        "rationale": rat,
        "source_qid": "4.1 / 4.2",
    }


def _integration_customer_concentration(target: dict) -> dict:
    """Kundenkonzentration als Risk-Indicator."""
    top1 = _safe_get(target, "customers", "top1_pct", default=0) or 0
    top3 = _safe_get(target, "customers", "top3_pct", default=0) or 0

    score = 100
    if top3 >= 60:
        score = 15
    elif top3 >= 50:
        score = 30
    elif top3 >= 40:
        score = 50
    elif top3 >= 30:
        score = 70
    elif top3 >= 20:
        score = 85

    if top1 >= 30:
        score = min(score, 25)
    elif top1 >= 20:
        score = min(score, 50)

    rat = f"Top-1: {top1}% · Top-3: {top3}%"
    if top3 >= 50:
        rat += " — sehr hohe Konzentration, Vertragsverlust = existenzbedrohend"
    elif top3 >= 35:
        rat += " — moderate Konzentration, Abhängigkeit beobachten"
    elif top3 < 25:
        rat += " — gut diversifizierte Kundenbasis"

    return {
        "name": "Customer Concentration",
        "score": _clamp(score),
        "rationale": rat,
        "source_qid": "3.2 / 3.3",
    }


def _integration_personnel_stability(target: dict) -> dict:
    """Personalstabilität: Fluktuation + Schlüsselperson-Risiko + Pensions-Welle."""
    turnover = _safe_get(target, "people", "turnover_12m_pct", default=0) or 0
    key_risk = _safe_get(target, "people", "key_person_risk", default=False)
    over_60 = _safe_get(target, "people", "employees_over_60", default=0) or 0
    fte_total = (
        (_safe_get(target, "people", "fte_property_manager", default=0) or 0)
        + (_safe_get(target, "people", "fte_accounting", default=0) or 0)
        + (_safe_get(target, "people", "fte_other", default=0) or 0)
    )

    over_60_pct = (over_60 / fte_total * 100) if fte_total > 0 else 0

    score = 100
    parts = []

    if turnover > 25:
        score -= 35
        parts.append(f"Fluktuation {turnover}% (sehr hoch)")
    elif turnover > 15:
        score -= 15
        parts.append(f"Fluktuation {turnover}% (über Branche)")
    else:
        parts.append(f"Fluktuation {turnover}% (stabil)")

    if key_risk:
        score -= 25
        parts.append("Schlüsselperson-Risiko identifiziert")

    if over_60_pct > 35:
        score -= 20
        parts.append(f"{over_60_pct:.0f}% MA > 60J (Pensions-Welle)")
    elif over_60_pct > 20:
        score -= 10
        parts.append(f"{over_60_pct:.0f}% MA > 60J")

    return {
        "name": "Personnel Stability",
        "score": _clamp(score),
        "rationale": " · ".join(parts),
        "source_qid": "5.6 / 5.8 / 5.11",
    }


def _integration_ownership_complexity(target: dict) -> dict:
    """Anzahl Gesellschafter + Mehrheit = wie schnell kommt Deal-Closing zustande."""
    n = _safe_get(target, "company_basics", "shareholders", default=1) or 1
    has_majority = _safe_get(target, "company_basics", "majority_shareholder", default=True)

    score = 100
    parts = []

    if n == 1:
        parts.append("1 Gesellschafter — saubere Entscheidungsstruktur")
    elif n <= 3:
        score -= 10
        parts.append(f"{n} Gesellschafter")
    elif n <= 5:
        score -= 25
        parts.append(f"{n} Gesellschafter — Komplexität bei Closing erwartbar")
    else:
        score -= 40
        parts.append(f"{n} Gesellschafter — komplexe Eigentümerstruktur")

    if not has_majority and n > 1:
        score -= 20
        parts.append("kein Mehrheitsgesellschafter — kein klarer Entscheider")

    return {
        "name": "Ownership Complexity",
        "score": _clamp(score),
        "rationale": " · ".join(parts),
        "source_qid": "1.6 / 1.7",
    }


# ──────────────────────────────────────────────────────────────────────────
# SYNERGY POTENTIAL — Sub-Scores
# ──────────────────────────────────────────────────────────────────────────
def _synergy_cross_sell(target: dict) -> dict:
    """Cross-Sell-Basis: Anzahl Eigentümer für Insurance/Energy/Brokerage."""
    weg_count = _safe_get(target, "portfolio", "weg_count", default=0) or 0
    units = _safe_get(target, "portfolio", "units_total", default=0) or 0

    # Approx Eigentümer-Anzahl: WEG-Eigentümer (ca. units in WEG-Anteil) + Mietverwalter (ca. 1 pro Mietobjekt)
    weg_pct = _safe_get(target, "portfolio", "weg_pct", default=0) or 0
    weg_units = units * weg_pct / 100
    approx_owners = weg_units + (weg_count * 0)  # WEG-Units ≈ WEG-Eigentümer

    if approx_owners >= 3000:
        score = 100
        rat = f"~{approx_owners:.0f} potenzielle Eigentümer für Cross-Sell — sehr starke Basis"
    elif approx_owners >= 1500:
        score = 85
        rat = f"~{approx_owners:.0f} potenzielle Eigentümer für Cross-Sell"
    elif approx_owners >= 800:
        score = 60
        rat = f"~{approx_owners:.0f} potenzielle Eigentümer — moderates Cross-Sell-Potenzial"
    elif approx_owners >= 300:
        score = 35
        rat = f"~{approx_owners:.0f} potenzielle Eigentümer — limitiertes Cross-Sell"
    else:
        score = 15
        rat = "Sehr kleine Eigentümer-Basis"

    return {
        "name": "Cross-Sell Base",
        "score": _clamp(score),
        "rationale": rat,
        "source_qid": "2.1 / 2.2 / 2.8",
    }


def _synergy_backoffice(target: dict) -> dict:
    """Backoffice-Konsolidierung-Potenzial: hoher Accounting-FTE-Anteil = mehr Synergie."""
    fte_acc = _safe_get(target, "people", "fte_accounting", default=0) or 0
    fte_pm = _safe_get(target, "people", "fte_property_manager", default=0) or 0
    fte_other = _safe_get(target, "people", "fte_other", default=0) or 0
    fte_total = fte_acc + fte_pm + fte_other

    if fte_total == 0:
        return {
            "name": "Backoffice Consolidation",
            "score": 50,
            "rationale": "Keine FTE-Daten",
            "source_qid": "5.1 / 5.2 / 5.3",
        }

    acc_pct = (fte_acc / fte_total) * 100

    if acc_pct >= 30:
        score = 95
        rat = f"{acc_pct:.0f}% der FTEs in Accounting — hohes Konsolidierungs-Potenzial"
    elif acc_pct >= 20:
        score = 75
        rat = f"{acc_pct:.0f}% der FTEs in Accounting — solides Potenzial"
    elif acc_pct >= 12:
        score = 50
        rat = f"{acc_pct:.0f}% der FTEs in Accounting — moderates Potenzial"
    else:
        score = 25
        rat = f"{acc_pct:.0f}% der FTEs in Accounting — limitiertes Potenzial"

    return {
        "name": "Backoffice Consolidation",
        "score": _clamp(score),
        "rationale": rat,
        "source_qid": "5.1 / 5.2 / 5.3",
    }


def _synergy_ai_automation(target: dict) -> dict:
    """AI-Automation-Gap: Manueller heute = mehr Wert durch Buena-Plattform."""
    digital_pct = _safe_get(target, "operations", "digital_owner_pct", default=0) or 0
    has_portal = _safe_get(target, "operations", "owner_portal", default=False)
    banking = _safe_get(target, "operations", "banking_integration", default="")
    minutes_digital = _safe_get(target, "operations", "weg_minutes_digital_pct", default=0) or 0

    score = 0  # higher = more gap = more synergy potential
    parts = []

    if not has_portal:
        score += 35
        parts.append("kein Owner-Portal")
    else:
        parts.append("Owner-Portal vorhanden")

    if digital_pct < 30:
        score += 25
        parts.append(f"nur {digital_pct}% digitale Owner-Kommunikation")
    elif digital_pct < 60:
        score += 15
        parts.append(f"{digital_pct}% digitale Owner-Kommunikation")

    if banking == "Manuell":
        score += 25
        parts.append("manueller Zahlungsverkehr")
    elif banking == "Halb-automatisch via Online-Banking":
        score += 12
        parts.append("halb-automatischer Zahlungsverkehr")

    if minutes_digital < 50:
        score += 15
        parts.append(f"nur {minutes_digital}% WEG-Protokolle digital archiviert")

    return {
        "name": "AI Automation Gap",
        "score": _clamp(score),
        "rationale": " · ".join(parts) if parts else "Hoher Digitalisierungsgrad",
        "source_qid": "4.4 / 4.5 / 4.6 / 4.10",
    }


def _synergy_pricing_lever(target: dict) -> dict:
    """Pricing-Hebel: lange ohne Erhöhung = sofortiger Wert-Hebel."""
    last_year = _safe_get(target, "customers", "last_price_increase_year", default=0) or 0

    if last_year == 0:
        return {
            "name": "Pricing Lever",
            "score": 50,
            "rationale": "Keine Daten zur letzten Preiserhöhung",
            "source_qid": "3.13a",
        }

    years_since = 2026 - last_year

    if years_since >= 5:
        score = 100
        rat = f"Letzte Preiserhöhung {last_year} ({years_since}J alt) — starker Hebel"
    elif years_since >= 3:
        score = 75
        rat = f"Letzte Preiserhöhung {last_year} ({years_since}J alt) — Hebel verfügbar"
    elif years_since >= 2:
        score = 50
        rat = f"Letzte Preiserhöhung {last_year} ({years_since}J alt) — moderater Hebel"
    else:
        score = 25
        rat = f"Preise erst {years_since}J alt — wenig Pricing-Spielraum kurzfristig"

    return {
        "name": "Pricing Lever",
        "score": _clamp(score),
        "rationale": rat,
        "source_qid": "3.13a",
    }


# ──────────────────────────────────────────────────────────────────────────
# Aggregation
# ──────────────────────────────────────────────────────────────────────────
def _aggregate_dimension(subscore_results: list, sub_weights: dict) -> dict:
    """Gewichtete Aggregation der Sub-Scores zu einem Dimension-Score."""
    # Normalisiere Sub-Weights (falls User welche edited hat, summieren sie nicht zu 1)
    weight_sum = sum(sub_weights.values()) or 1.0
    enriched = []
    total_score = 0.0

    for sub in subscore_results:
        # Map subscore name to weight key (lowercase + underscore)
        key = sub["name"].lower().replace(" ", "_").replace("-", "_").replace("&", "and")
        # Try direct match first
        weight = None
        for wk, wv in sub_weights.items():
            if wk == key or wk in key or key in wk:
                weight = wv
                break
        if weight is None:
            weight = list(sub_weights.values())[len(enriched)] if len(enriched) < len(sub_weights) else 0

        weight_norm = weight / weight_sum
        contribution = sub["score"] * weight_norm
        total_score += contribution

        enriched.append({
            **sub,
            "weight": weight_norm,
            "weighted_contribution": contribution,
        })

    return {
        "score": _clamp(total_score),
        "subscores": enriched,
    }


def compute_full_scores(
    target: dict,
    weights: dict | None = None,
    sub_weights: dict | None = None,
) -> dict:
    """
    Hauptfunktion: berechnet alle Scores mit voller Transparenz.

    Returns:
        {
            "overall_score": int,
            "weights": {...},
            "dimensions": {
                "strategic_fit": {"score": int, "subscores": [...]},
                "financial_health": {"score": int, "subscores": [...]},
                ...
            }
        }
    """
    w = weights or DEFAULT_WEIGHTS
    sw = sub_weights or DEFAULT_SUB_WEIGHTS

    # Strategic Fit
    sf_subs = [
        _strategic_size_fit(target),
        _strategic_succession_trigger(target),
        _strategic_transition_runway(target),
    ]
    strategic_fit = _aggregate_dimension(sf_subs, sw["strategic_fit"])

    # Financial Health
    fh_subs = [
        _financial_ebitda_margin(target),
        _financial_revenue_growth(target),
        _financial_working_capital(target),
        _financial_trustee_compliance(target),
    ]
    financial_health = _aggregate_dimension(fh_subs, sw["financial_health"])

    # Integration Complexity
    ic_subs = [
        _integration_software(target),
        _integration_customer_concentration(target),
        _integration_personnel_stability(target),
        _integration_ownership_complexity(target),
    ]
    integration_complexity = _aggregate_dimension(ic_subs, sw["integration_complexity"])

    # Synergy Potential
    sp_subs = [
        _synergy_cross_sell(target),
        _synergy_backoffice(target),
        _synergy_ai_automation(target),
        _synergy_pricing_lever(target),
    ]
    synergy_potential = _aggregate_dimension(sp_subs, sw["synergy_potential"])

    # Overall (gewichtete Top-Level)
    weight_sum_top = sum(w.values()) or 1.0
    overall = (
        strategic_fit["score"] * w["strategic_fit"] / weight_sum_top
        + financial_health["score"] * w["financial_health"] / weight_sum_top
        + integration_complexity["score"] * w["integration_complexity"] / weight_sum_top
        + synergy_potential["score"] * w["synergy_potential"] / weight_sum_top
    )

    return {
        "overall_score": _clamp(overall),
        "weights": w,
        "sub_weights": sw,
        "dimensions": {
            "strategic_fit": strategic_fit,
            "financial_health": financial_health,
            "integration_complexity": integration_complexity,
            "synergy_potential": synergy_potential,
        },
    }


# ──────────────────────────────────────────────────────────────────────────
# Backward-Compat: für target["scores"] Lookup
# ──────────────────────────────────────────────────────────────────────────
def compute_legacy_scores(target: dict) -> dict:
    """Kompatibilitäts-Wrapper für Code, der das alte 5-Felder-Format erwartet."""
    full = compute_full_scores(target)
    return {
        "strategic_fit": full["dimensions"]["strategic_fit"]["score"],
        "financial_health": full["dimensions"]["financial_health"]["score"],
        "integration_complexity": full["dimensions"]["integration_complexity"]["score"],
        "synergy_potential": full["dimensions"]["synergy_potential"]["score"],
        "overall_score": full["overall_score"],
    }


def has_knockouts(target: dict) -> tuple[bool, list]:
    """Prüft ob ein Target Knock-Out-Flags hat."""
    ko_data = target.get("knockouts", {})
    triggered = [k for k, v in ko_data.items() if v is True]
    return (len(triggered) > 0, triggered)


def compute_live_flags(target: dict) -> list[dict]:
    """
    Berechnet Flags direkt aus Target-Daten (nicht aus Form-Answers).
    Dies entspricht der DD-Auswertung — komplementär zum Sub-Score-Drill-Down.
    Returns list of {level, text}.
    """
    flags = []

    cb = target.get("company_basics", {}) or {}
    p = target.get("portfolio", {}) or {}
    c = target.get("customers", {}) or {}
    o = target.get("operations", {}) or {}
    pp = target.get("people", {}) or {}
    f = target.get("financials", {}) or {}

    # Company Basics
    fte = cb.get("fte_total", 0) or 0
    if fte > 40:
        flags.append({"level": "yellow", "text": f"{fte} FTE — Größe ggf. außerhalb Buena Sweet Spot"})
    sh = cb.get("shareholders", 1) or 1
    if sh > 4:
        flags.append({"level": "yellow", "text": f"{sh} Gesellschafter — komplexe Eigentümerstruktur"})
    if sh > 1 and not cb.get("majority_shareholder", True):
        flags.append({"level": "yellow", "text": "Kein Mehrheitsgesellschafter — kein klarer Entscheider"})
    age = cb.get("owner_age", 0) or 0
    if age >= 60:
        flags.append({"level": "green", "text": f"Inhaber {age}J — Nachfolge-Trigger wahrscheinlich"})
    if cb.get("sale_motivation") == "Finanzielle Notlage":
        flags.append({"level": "red", "text": "Verkaufsmotivation: Finanzielle Notlage — DD-Tiefe erhöhen"})
    if cb.get("transition_period") == "<3 Monate":
        flags.append({"level": "red", "text": "Übergangsperiode <3 Monate — Knowledge-Transfer-Risiko"})

    # Portfolio
    units = p.get("units_total", 0) or 0
    if 1500 <= units <= 8000:
        flags.append({"level": "green", "text": f"{units:,} Units im Buena Sweet Spot"})
    gewerbe = p.get("gewerbe_pct", 0) or 0
    if gewerbe > 30:
        flags.append({"level": "yellow", "text": f"Gewerbe-Anteil {gewerbe}% — separate DD erforderlich"})
    geo = p.get("geo_spread_km", 0) or 0
    if geo > 200:
        flags.append({"level": "yellow", "text": f"Geo-Streuung {geo} km — Logistik-Komplexität"})

    # Customers
    top1 = c.get("top1_pct", 0) or 0
    top3 = c.get("top3_pct", 0) or 0
    if top1 > 25:
        flags.append({"level": "red", "text": f"Top-1-Kunde = {top1}% vom Umsatz — sehr hohe Konzentration"})
    elif top1 > 15:
        flags.append({"level": "yellow", "text": f"Top-1-Kunde = {top1}% vom Umsatz — Konzentration"})
    if top3 > 50:
        flags.append({"level": "red", "text": f"Top-3 Kunden = {top3}% vom Umsatz — sehr hohe Konzentration"})
    elif top3 > 35:
        flags.append({"level": "yellow", "text": f"Top-3 Kunden = {top3}% vom Umsatz — Konzentration"})

    nrr = c.get("nrr_12m", 100) or 100
    if nrr < 90:
        flags.append({"level": "red", "text": f"NRR {nrr}% — hohe Churn"})

    last_pi = c.get("last_price_increase_year", 2026) or 2026
    if last_pi and (2026 - last_pi) >= 4:
        flags.append({"level": "green", "text": f"Letzte Preiserhöhung {last_pi} ({2026-last_pi}J alt) — Pricing-Hebel"})

    # Operations
    sw = o.get("primary_software", "")
    if sw == "Excel/Word":
        flags.append({"level": "red", "text": "Tech-Stack: Excel/Word — Migrations-Komplexität extrem"})
    elif sw == "Eigenbau":
        flags.append({"level": "yellow", "text": "Tech-Stack: Eigenbau — Custom-Mapping aufwendig"})
    if o.get("deployment") == "On-Prem":
        flags.append({"level": "yellow", "text": "On-Prem Deployment — Datenexport-Komplexität"})
    if not o.get("owner_portal", True):
        flags.append({"level": "green", "text": "Kein Owner-Portal vorhanden — Buena-Plattform = sofortiger Service-Upgrade"})

    # People
    if pp.get("key_person_risk"):
        flags.append({"level": "red", "text": "Schlüsselperson-Risiko identifiziert"})
    turnover = pp.get("turnover_12m_pct", 0) or 0
    if turnover > 25:
        flags.append({"level": "red", "text": f"Mitarbeiterfluktuation {turnover}% — Stabilitätsrisiko"})
    pcr = pp.get("personnel_cost_ratio", 0) or 0
    if pcr > 75:
        flags.append({"level": "red", "text": f"Personalkosten {pcr}% vom Umsatz — Margenkomprimierung"})
    elif pcr and pcr < 50:
        flags.append({"level": "green", "text": f"Personalkosten nur {pcr}% vom Umsatz — gesunde Struktur"})
    over_60 = pp.get("employees_over_60", 0) or 0
    fte_total = (
        (pp.get("fte_property_manager", 0) or 0)
        + (pp.get("fte_accounting", 0) or 0)
        + (pp.get("fte_other", 0) or 0)
    )
    if fte_total > 0 and (over_60 / fte_total) > 0.30:
        flags.append({"level": "yellow", "text": f"{over_60}/{fte_total} MA > 60J — Pensions-Welle"})

    # Financials — Margin Trend
    rev_y1 = f.get("revenue_y1") or 0
    rev_y2 = f.get("revenue_y2") or 0
    rev_y3 = f.get("revenue_y3") or 0
    eb_y1 = f.get("ebitda_y1") or 0
    eb_y2 = f.get("ebitda_y2") or 0
    eb_y3 = f.get("ebitda_y3") or 0
    if rev_y1 > 0 and rev_y3 > 0:
        m1 = eb_y1 / rev_y1 * 100
        m3 = eb_y3 / rev_y3 * 100
        if m3 - m1 > 1.5:
            flags.append({"level": "yellow", "text": f"EBITDA-Marge declining: {m3:.1f}% → {(eb_y2/rev_y2*100):.1f}% → {m1:.1f}%"})

    if f.get("tax_proceedings"):
        flags.append({"level": "red", "text": "Laufende Steuerprüfung — DD vertiefen"})

    return flags
