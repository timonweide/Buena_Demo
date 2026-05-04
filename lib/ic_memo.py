"""
Buena Piloto — IC-Memo Generator (Buena Design System)

Visuell am buena.com orientierten Investment-Committee-Memo:
- Schwarz/weiß, minimal, viel Whitespace
- Buena Quatrefoil-Logo oben links
- Claude API generiert Executive Summary (Fallback: strukturierter Mock)
- Stage-aware Sektionen

Reportlab wird lazy importiert (nur bei tatsächlicher PDF-Generation).
"""
import io
import os
from datetime import date
from pathlib import Path

from lib.scoring import compute_full_scores, compute_live_flags, has_knockouts
from lib.data_loader import calculate_derived_metrics

LOGO_PATH = Path(__file__).parent.parent / "data" / "buena_logo.png"

# ──────────────────────────────────────────────────────────────────────────
# Lazy reportlab globals
# ──────────────────────────────────────────────────────────────────────────
_RL_INITIALIZED = False
_G = {}   # holds all reportlab symbols


def _ensure_reportlab():
    global _RL_INITIALIZED, _G
    if _RL_INITIALIZED:
        return
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether,
    )
    from reportlab.platypus import Image as RLImage

    # ── Buena Color Palette ────────────────────────────────────────────────
    # Source: buena.com — near-monochromatic, clean, typographic
    _G["C_BLACK"]      = HexColor("#0A0A0A")   # headings, logo text
    _G["C_DARK"]       = HexColor("#2B2B2B")   # body text
    _G["C_MED"]        = HexColor("#6B6B6B")   # captions, labels
    _G["C_LIGHT"]      = HexColor("#ABABAB")   # faint labels
    _G["C_RULE"]       = HexColor("#D4D4D4")   # thin HR lines
    _G["C_ROW"]        = HexColor("#F5F5F5")   # alternate table rows
    _G["C_TAG_GREEN"]  = HexColor("#1A1A1A")   # pursue tag (inverted)
    _G["C_TAG_AMBER"]  = HexColor("#4B4B4B")   # caution tag
    _G["white"]        = white
    _G["black"]        = black

    # ── Styles ────────────────────────────────────────────────────────────
    base = getSampleStyleSheet()
    C = _G   # shorthand

    def ps(name, **kw):
        parent = kw.pop("parent", base["Normal"])
        return ParagraphStyle(name, parent=parent, **kw)

    _G["S"] = {
        # Cover
        "cover_logo_text": ps("clt",
            fontSize=22, fontName="Helvetica-Bold",
            textColor=C["C_BLACK"], leading=26, spaceAfter=0,
        ),
        "cover_subtitle": ps("csub",
            fontSize=10, fontName="Helvetica",
            textColor=C["C_MED"], leading=14, spaceAfter=0,
        ),
        "cover_target": ps("ctgt",
            fontSize=32, fontName="Helvetica-Bold",
            textColor=C["C_BLACK"], leading=38, spaceBefore=28, spaceAfter=4,
        ),
        "cover_meta": ps("cmeta",
            fontSize=11, fontName="Helvetica",
            textColor=C["C_MED"], leading=16, spaceAfter=4,
        ),
        # Section headers
        "h1": ps("h1",
            fontSize=11, fontName="Helvetica-Bold",
            textColor=C["C_BLACK"], spaceBefore=24, spaceAfter=6, leading=14,
        ),
        "h2": ps("h2",
            fontSize=9.5, fontName="Helvetica-Bold",
            textColor=C["C_MED"], spaceBefore=14, spaceAfter=4, leading=12,
        ),
        # Body
        "body": ps("body",
            fontSize=9.5, fontName="Helvetica",
            textColor=C["C_DARK"], leading=14, spaceAfter=5,
            alignment=TA_JUSTIFY,
        ),
        "body_left": ps("body_left",
            fontSize=9.5, fontName="Helvetica",
            textColor=C["C_DARK"], leading=14, spaceAfter=4,
        ),
        "bullet": ps("bullet",
            fontSize=9.5, fontName="Helvetica",
            textColor=C["C_DARK"], leading=14, spaceAfter=3,
            leftIndent=12, bulletIndent=0,
        ),
        "caption": ps("caption",
            fontSize=8, fontName="Helvetica",
            textColor=C["C_MED"], leading=10, spaceAfter=2,
        ),
        # Recommendation
        "rec_tag": ps("rec_tag",
            fontSize=9, fontName="Helvetica-Bold",
            textColor=C["C_MED"], leading=12, spaceAfter=2, alignment=TA_CENTER,
        ),
        "rec_verdict": ps("rec_verdict",
            fontSize=28, fontName="Helvetica-Bold",
            textColor=C["C_BLACK"], leading=32, spaceAfter=4, alignment=TA_CENTER,
        ),
        "rec_rationale": ps("rec_rat",
            fontSize=10, fontName="Helvetica",
            textColor=C["C_DARK"], leading=14, spaceAfter=0, alignment=TA_CENTER,
        ),
        # Table cells
        "tc": ps("tc",
            fontSize=9, fontName="Helvetica",
            textColor=C["C_DARK"], leading=12, spaceAfter=0,
        ),
        "tc_bold": ps("tc_bold",
            fontSize=9, fontName="Helvetica-Bold",
            textColor=C["C_BLACK"], leading=12, spaceAfter=0,
        ),
        "tc_head": ps("tc_head",
            fontSize=8.5, fontName="Helvetica-Bold",
            textColor=C["C_MED"], leading=11, spaceAfter=0,
        ),
        "tc_label": ps("tc_label",
            fontSize=8.5, fontName="Helvetica-Bold",
            textColor=C["C_MED"], leading=11, spaceAfter=0,
        ),
        # KPI
        "kpi_val": ps("kpiv",
            fontSize=20, fontName="Helvetica-Bold",
            textColor=C["C_BLACK"], leading=22, spaceAfter=0, alignment=TA_CENTER,
        ),
        "kpi_label": ps("kpil",
            fontSize=7.5, fontName="Helvetica",
            textColor=C["C_MED"], leading=10, spaceAfter=0, alignment=TA_CENTER,
        ),
    }

    # Store needed reportlab symbols
    _G["A4"] = A4
    _G["cm"] = cm
    _G["mm"] = mm
    _G["SimpleDocTemplate"] = SimpleDocTemplate
    _G["Paragraph"] = Paragraph
    _G["Spacer"] = Spacer
    _G["Table"] = Table
    _G["TableStyle"] = TableStyle
    _G["PageBreak"] = PageBreak
    _G["HRFlowable"] = HRFlowable
    _G["KeepTogether"] = KeepTogether
    _G["RLImage"] = RLImage
    _G["TA_LEFT"] = TA_LEFT
    _G["TA_CENTER"] = TA_CENTER
    _G["TA_RIGHT"] = TA_RIGHT
    _RL_INITIALIZED = True


# ──────────────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────────────
def _fmt_eur(val, k=False):
    if not val:
        return "—"
    if k and abs(val) >= 1_000_000:
        return f"€{val/1_000_000:,.1f}M".replace(",", ".")
    if k and abs(val) >= 1000:
        return f"€{val/1000:,.0f}k".replace(",", ".")
    return f"€{val:,.0f}".replace(",", ".")


def _fmt_pct(val):
    if val is None:
        return "—"
    return f"{val:.1f} %"


def _hr():
    """Thin Buena-style horizontal rule."""
    return _G["HRFlowable"](
        width="100%", thickness=0.5, color=_G["C_RULE"],
        spaceAfter=6, spaceBefore=6,
    )


def _kv(rows, col_widths=None):
    """Clean label → value table, no borders."""
    P, S, C = _G["Paragraph"], _G["S"], _G
    col_widths = col_widths or [5 * _G["cm"], 11.5 * _G["cm"]]
    data = [[P(k, S["tc_label"]), P(str(v), S["body_left"])] for k, v in rows]
    t = _G["Table"](data, colWidths=col_widths)
    t.setStyle(_G["TableStyle"]([
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def _data_table(data, col_widths):
    """Minimal bordered data table with alt row shading."""
    t = _G["Table"](data, colWidths=col_widths)
    t.setStyle(_G["TableStyle"]([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), _G["C_BLACK"]),
        ("TEXTCOLOR", (0, 0), (-1, 0), _G["white"]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        # Data rows
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), _G["C_DARK"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_G["white"], _G["C_ROW"]]),
        # Padding
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Bottom border only
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, _G["C_RULE"]),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, _G["C_RULE"]),
    ]))
    return t


def _section_header(title):
    P, S = _G["Paragraph"], _G["S"]
    return [
        _hr(),
        P(title.upper(), S["h1"]),
    ]


# ──────────────────────────────────────────────────────────────────────────
# Claude Executive Summary
# ──────────────────────────────────────────────────────────────────────────
def _generate_executive_summary(target: dict, full_scores: dict, flags: list) -> str:
    """
    Generates a 3-4 sentence M&A-style executive summary via Claude API.
    Falls back to a structured template if no API key is set.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    cb = target.get("company_basics", {})
    p = target.get("portfolio", {})
    f = target.get("financials", {})
    overall = full_scores["overall_score"]
    units = p.get("units_total", 0)
    rev = f.get("revenue_y1", 0)
    eb = f.get("ebitda_y1", 0)
    margin = (eb / rev * 100) if rev > 0 else 0
    stage = target.get("status", "")
    name = target.get("name", "Target")
    location = target.get("location", "")

    red_flags = [fl["text"] for fl in flags if fl["level"] == "red"]
    green_flags = [fl["text"] for fl in flags if fl["level"] == "green"]

    rec = "PURSUE" if overall >= 70 else "PURSUE WITH CAUTION" if overall >= 50 else "PASS"

    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""You are writing an Investment Committee memo for Buena GmbH, 
a Berlin-based property management company that acquires and professionalizes Hausverwaltungen.

Write a concise 3-4 sentence executive summary (in German) for this acquisition target:

Target: {name} ({location})
Stage: {stage}
Units under management: {units:,}
Revenue Y1: €{rev:,.0f}
EBITDA Y1: €{eb:,.0f} ({margin:.1f}% margin)
Owner age: {cb.get("owner_age", "—")}, Sale motivation: {cb.get("sale_motivation", "—")}
Transition period: {cb.get("transition_period", "—")}
Overall Score: {overall}/100
Recommendation: {rec}
Key risks: {"; ".join(red_flags[:2]) if red_flags else "keine kritischen Flags"}
Key strengths: {"; ".join(green_flags[:2]) if green_flags else "—"}

Write exactly 3-4 sentences. Tone: direct, analytical, investment-grade. 
No bullet points. Start with the target name. End with the recommendation."""

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()

        except Exception:
            pass  # Fall through to template

    # ── Template fallback ──
    motivation_text = {
        "Nachfolge": "ein altersbedingter Eigentümerwechsel",
        "Strategischer Exit": "ein strategischer Verkauf",
        "Finanzielle Notlage": "ein notlagebedingter Verkauf",
    }.get(cb.get("sale_motivation", ""), "ein geplanter Eigentümerwechsel")

    flag_text = ""
    if red_flags:
        flag_text = f" Als zentrale Risikofelder wurden identifiziert: {red_flags[0].rstrip('.')}."

    rec_text = {
        "PURSUE": "Aufgrund des soliden Gesamtprofils empfehlen wir die Weiterführung des Prozesses und die Abgabe eines indikativen Angebots.",
        "PURSUE WITH CAUTION": "Vor Angebotsabgabe sollten die identifizierten Risikofelder in einer vertieften Due Diligence adressiert werden.",
        "PASS": "Angesichts der Gesamtbewertung empfehlen wir, dieses Target nicht weiterzuverfolgen.",
    }[rec]

    return (
        f"{name} mit Sitz in {location} ist eine Hausverwaltung mit {units:,} verwalteten Einheiten, "
        f"einem Jahresumsatz von {_fmt_eur(rev)} und einer EBITDA-Marge von {margin:.1f} %. "
        f"Der Anlass des Verkaufs ist {motivation_text} bei einem Inhaber im Alter von {cb.get('owner_age', '—')} Jahren.{flag_text} "
        f"{rec_text}"
    )


# ──────────────────────────────────────────────────────────────────────────
# Section Builders
# ──────────────────────────────────────────────────────────────────────────
def _build_cover(target, full_scores, flags):
    P, S, C = _G["Paragraph"], _G["S"], _G
    story = []

    # ── Logo + Buena wordmark ───────────────────────────────────────────
    logo_cells = []
    if LOGO_PATH.exists():
        logo_img = C["RLImage"](str(LOGO_PATH), width=1.2 * C["cm"], height=1.2 * C["cm"])
        logo_cells = [[logo_img, P("Buena", S["cover_logo_text"])]]
    else:
        logo_cells = [["", P("Buena", S["cover_logo_text"])]]

    logo_t = C["Table"](logo_cells, colWidths=[1.5 * C["cm"], 6 * C["cm"]])
    logo_t.setStyle(C["TableStyle"]([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # Right side: stage + date
    meta_t = C["Table"]([[
        P(f"{target.get('status', '').upper()}", S["tc_head"]),
        P(date.today().strftime("%d.%m.%Y"), S["tc_head"]),
    ]], colWidths=[4 * C["cm"], 4.5 * C["cm"]])
    meta_t.setStyle(C["TableStyle"]([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    header_t = C["Table"]([[logo_t, meta_t]], colWidths=[8.5 * C["cm"], 9 * C["cm"]])
    header_t.setStyle(C["TableStyle"]([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_t)

    # ── Thin rule ───────────────────────────────────────────────────────
    story.append(C["Spacer"](1, 0.4 * C["cm"]))
    story.append(_hr())
    story.append(C["Spacer"](1, 0.6 * C["cm"]))

    # ── Target Name ────────────────────────────────────────────────────
    story.append(P("Investment Committee Memo", S["cover_subtitle"]))
    story.append(P(target.get("name", "—"), S["cover_target"]))
    story.append(P(
        f"{target.get('location', '—')}  ·  {target['portfolio'].get('units_total', 0):,} Units  ·  "
        f"Prepared by Buena Acquisitions",
        S["cover_meta"],
    ))

    story.append(C["Spacer"](1, 1.2 * C["cm"]))

    # ── Recommendation ─────────────────────────────────────────────────
    overall = full_scores["overall_score"]
    ko_active, _ = has_knockouts(target)

    if ko_active:
        verdict, rationale = "PASS", "Knock-Out Kriterien wurden getriggert."
    elif overall >= 70:
        verdict = "PURSUE"
        rationale = f"Starkes Investmentprofil. Score {overall}/100."
    elif overall >= 50:
        verdict = "PURSUE WITH CAUTION"
        rationale = f"Vertiefte DD erforderlich. Score {overall}/100."
    else:
        verdict = "PASS"
        rationale = f"Unter Investment-Threshold. Score {overall}/100."

    rec_table = C["Table"]([
        [P("RECOMMENDATION", S["rec_tag"])],
        [P(verdict, S["rec_verdict"])],
        [P(rationale, S["rec_rationale"])],
    ], colWidths=[17 * C["cm"]])
    rec_table.setStyle(C["TableStyle"]([
        ("BOX", (0, 0), (-1, -1), 1, C["C_BLACK"]),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(rec_table)

    story.append(C["Spacer"](1, 1 * C["cm"]))

    # ── KPI Strip ──────────────────────────────────────────────────────
    f = target.get("financials", {})
    rev = f.get("revenue_y1", 0)
    eb = f.get("ebitda_y1", 0)
    margin = (eb / rev * 100) if rev > 0 else 0

    kpis = [
        (f"{overall}", "Score"),
        (f"{target['portfolio'].get('units_total', 0):,}".replace(",", "."), "Units"),
        (_fmt_eur(rev, k=True), "Umsatz Y1"),
        (_fmt_eur(eb, k=True), "EBITDA Y1"),
        (f"{margin:.1f} %", "EBITDA-Marge"),
        (f"{target['company_basics'].get('owner_age', '—')} J.", "Inhaber-Alter"),
    ]

    kpi_row1 = [P(v, S["kpi_val"]) for v, _ in kpis]
    kpi_row2 = [P(l, S["kpi_label"]) for _, l in kpis]
    kpi_t = C["Table"]([kpi_row1, kpi_row2],
                        colWidths=[17 / 6 * C["cm"]] * 6,
                        rowHeights=[2.0 * C["cm"], 0.5 * C["cm"]])
    kpi_t.setStyle(C["TableStyle"]([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, C["C_RULE"]),
        ("LINEBELOW", (0, 1), (-1, 1), 0.5, C["C_RULE"]),
        # Vertical dividers between KPIs
        *[("LINEBEFORE", (i, 0), (i, 1), 0.5, C["C_RULE"]) for i in range(1, 6)],
    ]))
    story.append(kpi_t)

    return story


def _build_executive_summary(target, full_scores, flags):
    P, S, C = _G["Paragraph"], _G["S"], _G
    story = []
    story += _section_header("Executive Summary")

    # Generate via Claude (or template)
    summary_text = _generate_executive_summary(target, full_scores, flags)
    story.append(P(summary_text, S["body"]))

    # Top Drivers + Top Risks in 2 columns
    story.append(C["Spacer"](1, 0.4 * C["cm"]))
    all_subs = []
    for dim_name, dim_data in full_scores["dimensions"].items():
        for sub in dim_data["subscores"]:
            all_subs.append((dim_name, sub))

    drivers = sorted(all_subs, key=lambda x: -x[1]["score"])[:3]
    risks = sorted(all_subs, key=lambda x: x[1]["score"])[:3]
    red_flags = [fl for fl in flags if fl["level"] == "red"]

    def bullet_list(items, is_risk=False):
        lines = []
        for item in items:
            if isinstance(item, dict):
                # flag dict
                lines.append(P(f"— {item['text']}", S["bullet"]))
            else:
                dim, sub = item
                lines.append(P(f"— {sub['name']} ({sub['score']}/100)", S["bullet"]))
                lines.append(P(f"   {sub['rationale'][:80]}{'…' if len(sub['rationale'])>80 else ''}", S["caption"]))
        return lines

    col_drivers = [P("KEY DRIVERS", S["tc_head"])] + bullet_list(drivers)
    col_risks = [P("KEY RISKS", S["tc_head"])] + (
        bullet_list(red_flags[:3]) if red_flags else bullet_list(risks)
    )

    # Pad to same length for table
    max_len = max(len(col_drivers), len(col_risks))
    col_drivers += [P("", S["body"])] * (max_len - len(col_drivers))
    col_risks += [P("", S["body"])] * (max_len - len(col_risks))

    col_t = C["Table"](
        [[d, r] for d, r in zip(col_drivers, col_risks)],
        colWidths=[8.2 * C["cm"], 8.8 * C["cm"]],
    )
    col_t.setStyle(C["TableStyle"]([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBEFORE", (1, 0), (1, -1), 0.5, C["C_RULE"]),
        ("LEFTPADDING", (1, 0), (1, -1), 12),
    ]))
    story.append(col_t)
    return story


def _build_company_profile(target):
    P, S, C = _G["Paragraph"], _G["S"], _G
    story = _section_header("Company Profile")
    cb = target.get("company_basics", {})
    p = target.get("portfolio", {})
    pp = target.get("people", {})
    fte_pm = pp.get("fte_property_manager", 0) or 0
    fte_acc = pp.get("fte_accounting", 0) or 0
    fte_oth = pp.get("fte_other", 0) or 0

    rows = [
        ("Standort", target.get("location", "—")),
        ("Rechtsform / Gegründet", f"{cb.get('legal_form', '—')} / {cb.get('founded', '—')}"),
        ("Inhaber", f"{cb.get('owner_age', '—')} Jahre · Motivation: {cb.get('sale_motivation', '—')}"),
        ("Übergangsperiode", cb.get("transition_period", "—")),
        ("Gesellschafterstruktur", f"{cb.get('shareholders', 1)} Gesellschafter{'r' if cb.get('shareholders',1)==1 else ''} · {'mit' if cb.get('majority_shareholder') else 'ohne'} Mehrheit"),
        ("Mitarbeiter (FTE)", f"{fte_pm+fte_acc+fte_oth} gesamt  ·  {fte_pm} PM  ·  {fte_acc} Buchhaltung"),
        ("Portfolio", f"{p.get('units_total', 0):,} Units  ·  WEG {p.get('weg_pct',0)} %  ·  Miet {p.get('miet_pct',0)} %  ·  SEV {p.get('sondereig_pct',0)} %"),
        ("WEG-Anzahl / Geo", f"{p.get('weg_count', '—')} WEGs  ·  {p.get('geo_spread_km', '—')} km Streuung"),
    ]
    story.append(_kv(rows))
    return story


def _build_investment_thesis(target, full_scores):
    P, S, C = _G["Paragraph"], _G["S"], _G
    story = _section_header("Investment Thesis")

    P_, S_ = _G["Paragraph"], _G["S"]
    overall = full_scores["overall_score"]
    story.append(P_(
        f"Buena Piloto Score: <b>{overall}/100</b>  ·  Deterministisch aus DD-Daten berechnet.",
        S_["body_left"],
    ))
    story.append(C["Spacer"](1, 0.3 * C["cm"]))

    dim_meta = [
        ("strategic_fit", "Strategic Fit"),
        ("financial_health", "Financial Health"),
        ("integration_complexity", "Integration Complexity"),
        ("synergy_potential", "Synergy Potential"),
    ]
    rows = [[
        P_("DIMENSION", S_["tc_head"]),
        P_("SCORE", S_["tc_head"]),
        P_("TOP TREIBER", S_["tc_head"]),
        P_("BEGRÜNDUNG", S_["tc_head"]),
    ]]
    for dk, dl in dim_meta:
        dim = full_scores["dimensions"][dk]
        best = max(dim["subscores"], key=lambda s: s["score"])
        rat = best["rationale"]
        rows.append([
            P_(dl, S_["tc"]),
            P_(f"<b>{dim['score']}/100</b>", S_["tc_bold"]),
            P_(best["name"], S_["tc"]),
            P_(rat[:70] + ("…" if len(rat) > 70 else ""), S_["tc"]),
        ])
    story.append(_data_table(rows, [3.8*C["cm"], 1.8*C["cm"], 3.8*C["cm"], 7.6*C["cm"]]))
    return story


def _build_financials(target, parsed_pnl=None):
    P, S, C = _G["Paragraph"], _G["S"], _G
    story = _section_header("Financial Profile")
    f = target.get("financials", {})

    rev1 = f.get("revenue_y1", 0) or 0
    rev2 = f.get("revenue_y2", 0) or 0
    rev3 = f.get("revenue_y3", 0) or 0
    eb1 = f.get("ebitda_y1", 0) or 0
    eb2 = f.get("ebitda_y2", 0) or 0
    eb3 = f.get("ebitda_y3", 0) or 0

    def m(eb, rev):
        return f"{eb/rev*100:.1f} %" if rev else "—"

    cagr = (((rev1/rev3)**0.5-1)*100) if rev3 > 0 else None

    rows = [
        [P("", S["tc_head"]),
         P("Y3", S["tc_head"]), P("Y2", S["tc_head"]),
         P("Y1", S["tc_head"]), P("CAGR 3J", S["tc_head"])],
        [P("Umsatz", S["tc"]),
         P(_fmt_eur(rev3), S["tc"]), P(_fmt_eur(rev2), S["tc"]),
         P(_fmt_eur(rev1), S["tc"]), P(f"{cagr:.1f} %" if cagr is not None else "—", S["tc"])],
        [P("EBITDA", S["tc"]),
         P(_fmt_eur(eb3), S["tc"]), P(_fmt_eur(eb2), S["tc"]),
         P(_fmt_eur(eb1), S["tc"]), P("—", S["tc"])],
        [P("EBITDA-Marge", S["tc_bold"]),
         P(m(eb3,rev3), S["tc_bold"]), P(m(eb2,rev2), S["tc_bold"]),
         P(m(eb1,rev1), S["tc_bold"]), P("—", S["tc"])],
    ]

    story.append(_data_table(rows, [3.5*C["cm"], 3*C["cm"], 3*C["cm"], 3*C["cm"], 3*C["cm"]]))

    story.append(C["Spacer"](1, 0.4*C["cm"]))
    extra = [
        ("Bankkredit", _fmt_eur(f.get("existing_debt", 0))),
        ("AR > 90d", _fmt_eur(f.get("ar_over_90d", 0))),
        ("Treuhandmittel", _fmt_eur(f.get("trustee_funds", 0))),
    ]
    story.append(_kv(extra))

    if parsed_pnl:
        peb = parsed_pnl["subtotals"]["EBITDA"]
        prev = parsed_pnl["subtotals"]["Revenue Total"]
        pmg = parsed_pnl["ebitda_margin_pct"]
        self_m = (eb1/rev1*100) if rev1 > 0 else 0
        story.append(C["Spacer"](1, 0.3*C["cm"]))
        delta_text = f"Δ EBITDA: {_fmt_eur(peb-eb1)} ({pmg-self_m:+.1f} pp)"
        story.append(P(
            f"<b>AI-parsed BWA:</b> Umsatz {_fmt_eur(prev)}  ·  EBITDA {_fmt_eur(peb)} ({pmg:.1f} %)  ·  {delta_text}",
            S["body_left"],
        ))
        if eb1 > 0 and abs(peb - eb1) > eb1 * 0.2:
            story.append(P(
                "Significante Abweichung zum Self-Reported-Wert — DD-Daten überarbeiten.",
                S["caption"],
            ))
    return story


def _build_risks(flags, ko):
    P, S, C = _G["Paragraph"], _G["S"], _G
    story = _section_header("Risk Analysis")

    ko_active, ko_list = ko
    if ko_active:
        story.append(P(f"<b>KNOCK-OUT:</b> {', '.join(ko_list)}. DD-Pause empfohlen.", S["body_left"]))
        story.append(C["Spacer"](1, 0.2*C["cm"]))

    groups = [
        ("RED FLAGS", [f for f in flags if f["level"] == "red"]),
        ("YELLOW FLAGS", [f for f in flags if f["level"] == "yellow"]),
        ("POSITIVE", [f for f in flags if f["level"] == "green"]),
    ]
    for label, items in groups:
        if not items:
            continue
        story.append(P(f"{label} ({len(items)})", S["h2"]))
        for fl in items:
            story.append(P(f"— {fl['text']}", S["bullet"]))
    return story


def _build_lbo(lbo_inputs, lbo_result):
    P, S, C = _G["Paragraph"], _G["S"], _G
    story = _section_header("LBO Returns Analysis")

    if not lbo_result:
        story.append(P("LBO-Modell noch nicht konfiguriert.", S["body"]))
        return story

    holding = int(lbo_inputs["holding_period_years"])
    su_rows = [
        ("Purchase Price", f"{_fmt_eur(lbo_result['purchase_price'])}  ({lbo_inputs['entry_ebitda_multiple']:.1f}x EBITDA)"),
        ("Debt / Equity", f"{_fmt_eur(lbo_result['debt'])}  /  {_fmt_eur(lbo_result['equity'])}  ({int(lbo_inputs['debt_pct'])} % leverage)"),
    ]
    ret_rows = [
        ("Holding Period / Exit Multiple", f"{holding} Jahre  ·  {lbo_inputs['exit_ebitda_multiple']:.1f}x"),
        (f"Exit EBITDA (Y{holding})", _fmt_eur(lbo_result["exit_ebitda"])),
        ("Exit Equity Value", _fmt_eur(lbo_result["exit_equity"])),
        ("MoM / IRR", f"{lbo_result['mom']:.2f}x  ·  {lbo_result['irr_pct']:.1f} %"),
    ]
    eos = lbo_result["earnout_summary"]
    if lbo_inputs.get("earnout_amount", 0) > 0:
        status = f"triggered Y{eos['year']}" if eos["triggered"] else "nicht getriggert"
        ret_rows.append(("Earn-Out", f"{_fmt_eur(lbo_inputs['earnout_amount'])}  ·  {status}"))

    all_rows = [("SOURCES & USES", ""), *su_rows, ("", ""), ("EXIT & RETURNS", ""), *ret_rows]
    for label, val in all_rows:
        if label == "" and val == "":
            story.append(C["Spacer"](1, 0.2*C["cm"]))
        elif val == "":
            story.append(P(label, S["h2"]))
        else:
            story.append(_kv([(label, val)]))

    # Compact Year-by-Year
    story.append(C["Spacer"](1, 0.4*C["cm"]))
    story.append(P("YEAR-BY-YEAR ÜBERSICHT", S["h2"]))
    yby = [["Jahr", "Revenue", "EBITDA", "FCF", "Ending Debt"]]
    for y in lbo_result["yearly_data"][:min(7, len(lbo_result["yearly_data"]))]:
        yby.append([
            f"Y{y['year']}",
            _fmt_eur(y["revenue"], k=True),
            _fmt_eur(y["ebitda"], k=True),
            _fmt_eur(y["fcf_post_earnout"], k=True),
            _fmt_eur(y["ending_debt"], k=True),
        ])
    yby[0] = [P(c, S["tc_head"]) for c in yby[0]]
    story.append(_data_table(yby, [1.5*C["cm"], 3.8*C["cm"], 3.5*C["cm"], 3.5*C["cm"], 4.2*C["cm"]]))
    return story


def _build_pmi(target, pmi_plan, pmi_state):
    P, S, C = _G["Paragraph"], _G["S"], _G
    story = _section_header("PMI Plan")

    if not pmi_plan:
        story.append(P("PMI-Playbook noch nicht konfiguriert.", S["body"]))
        return story

    applied = pmi_plan.get("applied_rules", [])
    if applied:
        story.append(P(f"Auto-Plan aktiv: {len(applied)} DD-Regeln angewendet.", S["body_left"]))
        for rule in applied:
            story.append(P(f"— {rule['trigger_text']}", S["bullet"]))
        story.append(C["Spacer"](1, 0.3*C["cm"]))

    # Workstream summary
    ws_rows = [["WORKSTREAM", "TOTAL", "DONE", "AUTO"]]
    for ws in pmi_plan["workstreams"]:
        total = len(ws["tasks"])
        done = sum(1 for t in ws["tasks"] if pmi_state.get(t["id"], {}).get("status") == "Done")
        auto = sum(1 for t in ws["tasks"] if t.get("auto_generated") or t.get("auto_modified"))
        ws_rows.append([ws["name"], str(total), str(done), str(auto) if auto else "—"])
    ws_rows[0] = [P(c, S["tc_head"]) for c in ws_rows[0]]
    story.append(_data_table(ws_rows, [7*C["cm"], 3*C["cm"], 3*C["cm"], 4*C["cm"]]))

    # Critical path Day 1-30
    story.append(C["Spacer"](1, 0.4*C["cm"]))
    story.append(P("CRITICAL PATH — DAY 1–30", S["h2"]))
    crit = []
    for ws in pmi_plan["workstreams"]:
        for t in ws["tasks"]:
            timing = str(t["timing_days_after_close"])
            try:
                first_day = int(timing.split("-")[0].strip())
                if first_day <= 30:
                    crit.append((first_day, t))
            except (ValueError, IndexError):
                pass
    crit.sort(key=lambda x: x[0])
    cp_rows = [["DAY", "TASK", "OWNER"]]
    for day, t in crit[:7]:
        badge = " [AUTO]" if t.get("auto_generated") else ""
        cp_rows.append([f"D{t['timing_days_after_close']}", t["name"] + badge, t["default_owner"]])
    cp_rows[0] = [P(c, S["tc_head"]) for c in cp_rows[0]]
    story.append(_data_table(cp_rows, [2.5*C["cm"], 8.5*C["cm"], 6*C["cm"]]))
    return story


def _build_recommendation(target, full_scores, ko):
    P, S, C = _G["Paragraph"], _G["S"], _G
    story = _section_header("Recommendation")
    overall = full_scores["overall_score"]
    ko_active, _ = ko

    if ko_active:
        body = (
            f"<b>PASS.</b> Knock-Out Kriterien wurden positiv beantwortet. "
            f"Eine Weiterführung ist erst nach abschließender Klärung sinnvoll."
        )
    elif overall >= 70:
        body = (
            f"<b>PURSUE.</b> Score {overall}/100 bestätigt ein starkes Investmentprofil. "
            f"Empfehlung: LOI-Abgabe binnen 14 Tagen, parallel vertiefte Commercial DD."
        )
    elif overall >= 50:
        body = (
            f"<b>PURSUE WITH CAUTION.</b> Score {overall}/100 — Borderline. "
            f"Identifizierte Risikofelder in 30-tägiger vertiefter DD adressieren, "
            f"danach erneute IC-Vorlage."
        )
    else:
        body = (
            f"<b>PASS.</b> Score {overall}/100 unterschreitet Buenas Investment-Threshold. "
            f"Target nicht weiterverfolgen."
        )
    story.append(P(body, S["body"]))
    return story


# ──────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────────────────────────────────
def generate_ic_memo(
    target: dict,
    weights: dict | None = None,
    parsed_pnl: dict | None = None,
    lbo_inputs: dict | None = None,
    lbo_result: dict | None = None,
    pmi_plan: dict | None = None,
    pmi_state: dict | None = None,
) -> bytes:
    """
    Generates Buena-branded IC Memo PDF.
    Returns bytes. reportlab is imported lazily.
    """
    _ensure_reportlab()

    full_scores = compute_full_scores(target, weights=weights)
    flags = compute_live_flags(target)
    ko = has_knockouts(target)
    stage = target.get("status", "Outreach")
    stage_idx = {"Outreach": 0, "DD": 1, "Offer Accepted": 2}.get(stage, 0)

    buf = io.BytesIO()
    doc = _G["SimpleDocTemplate"](
        buf,
        pagesize=_G["A4"],
        leftMargin=2.2 * _G["cm"],
        rightMargin=2.2 * _G["cm"],
        topMargin=1.8 * _G["cm"],
        bottomMargin=1.8 * _G["cm"],
        title=f"IC Memo — {target.get('name', '')}",
        author="Buena Acquisitions",
    )

    story = []

    # Cover + Executive Summary always
    story += _build_cover(target, full_scores, flags)
    story.append(_G["Spacer"](1, 0.6 * _G["cm"]))
    story += _build_executive_summary(target, full_scores, flags)

    # Company Profile + Investment Thesis always
    story += _build_company_profile(target)
    story += _build_investment_thesis(target, full_scores)
    story += _build_risks(flags, ko)

    # DD+ sections
    if stage_idx >= 1:
        story += _build_financials(target, parsed_pnl=parsed_pnl)
        story += _build_lbo(lbo_inputs, lbo_result)

    # Offer Accepted
    if stage_idx >= 2:
        story += _build_pmi(target, pmi_plan, pmi_state or {})

    story += _build_recommendation(target, full_scores, ko)

    # Footer rule
    story.append(_G["Spacer"](1, 0.8 * _G["cm"]))
    story.append(_hr())
    story.append(_G["Paragraph"](
        f"Buena GmbH  ·  Berlin  ·  IC Memo  ·  Vertraulich  ·  {date.today().strftime('%d.%m.%Y')}",
        _G["S"]["caption"],
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
