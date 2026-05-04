"""
Seller Portal — Fully Functional DD Intake (v2: no-expander layout)
- Schema-driven Form-Auto-Rendering
- Live Conditional Logic
- Real-time Progress Bar (only updated when navigating, not on every keystroke)
- Validation
- Submit erstellt neues Target im Internal Dashboard

Bug-Fix v2:
- Keine Expander mehr — Sektionen sind als immer-sichtbare Cards gestylt.
  Damit verschwindet das "Kategorie klappt zu beim Tippen"-Problem.
- Sticky-TOC oben für Quick-Navigation zwischen Sektionen.
"""
import streamlit as st
from datetime import date
from lib.data_loader import load_dd_schema, add_target
from lib.form_engine import (
    is_question_visible,
    calculate_progress,
    validate_answers,
    form_answers_to_target,
)

st.set_page_config(
    page_title="Buena Acquisitions · Übergabe-Fragebogen",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────────────────
# CSS — Hide internal sidebar nav, style seller view, persistent section cards
# ──────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none; }
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }

    .seller-hero {
        background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%);
        color: white;
        padding: 32px;
        border-radius: 12px;
        margin-bottom: 24px;
    }
    .seller-hero h1 { color: white; margin: 0; font-size: 28px; }
    .seller-hero p { color: #DBEAFE; margin-top: 8px; font-size: 15px; }

    .seller-progress-wrap {
        background: white;
        padding: 16px 20px;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        margin-bottom: 16px;
    }

    .seller-toc {
        background: #F9FAFB;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 24px;
        font-size: 13px;
    }
    .seller-toc a {
        color: #1D4ED8;
        text-decoration: none;
        margin-right: 14px;
        white-space: nowrap;
    }
    .seller-toc a:hover { text-decoration: underline; }

    .seller-section-header {
        background: #1D4ED8;
        color: white;
        padding: 12px 20px;
        border-radius: 8px 8px 0 0;
        font-weight: 700;
        font-size: 16px;
        margin-top: 24px;
    }
    .seller-section-body {
        background: white;
        padding: 20px 24px 8px 24px;
        border: 1px solid #E5E7EB;
        border-top: none;
        border-radius: 0 0 8px 8px;
        margin-bottom: 8px;
    }
    .seller-section-intro {
        color: #4B5563;
        font-size: 14px;
        margin-bottom: 16px;
        font-style: italic;
    }
    .seller-section-progress {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.85);
        font-weight: 500;
    }

    .seller-footer {
        text-align: center;
        margin-top: 40px;
        color: #6B7280;
        font-size: 13px;
    }
    .submitted-card {
        background: #ECFDF5;
        border: 2px solid #10B981;
        border-radius: 12px;
        padding: 28px;
        text-align: center;
    }
    .submitted-card h2 { color: #065F46; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────
# Session-State Initialization
# ──────────────────────────────────────────────────────────────────────────
if "seller_answers" not in st.session_state:
    st.session_state["seller_answers"] = {}
if "seller_submitted" not in st.session_state:
    st.session_state["seller_submitted"] = False
if "seller_submission_meta" not in st.session_state:
    st.session_state["seller_submission_meta"] = None
# Stores actual file bytes for Q 6.12 (BWA upload) — separate from text answers
if "seller_bwa_files" not in st.session_state:
    st.session_state["seller_bwa_files"] = []

answers = st.session_state["seller_answers"]
schema = load_dd_schema()


# ──────────────────────────────────────────────────────────────────────────
# Seller-friendly section name overrides (Display only, nicht Datenstruktur)
# ──────────────────────────────────────────────────────────────────────────
SELLER_SECTION_NAME_OVERRIDES = {
    "knockouts": "Legal & Compliance",
}

SELLER_SECTION_ICON_OVERRIDES = {
    "knockouts": "⚖️",
}


def seller_section_display(cat: dict) -> tuple[str, str]:
    """Liefert (icon, short_name) mit Seller-Override falls vorhanden."""
    cat_id = cat["id"]
    icon = SELLER_SECTION_ICON_OVERRIDES.get(cat_id, cat["icon"])
    if cat_id in SELLER_SECTION_NAME_OVERRIDES:
        return icon, SELLER_SECTION_NAME_OVERRIDES[cat_id]
    return icon, cat["name"].split(". ", 1)[-1]


# ──────────────────────────────────────────────────────────────────────────
# Post-Submit Confirmation Screen
# ──────────────────────────────────────────────────────────────────────────
if st.session_state["seller_submitted"] and st.session_state["seller_submission_meta"]:
    meta = st.session_state["seller_submission_meta"]
    follow_up = (
        "Sie werden innerhalb von 5 Werktagen kontaktiert"
        if meta["completion_pct"] < 100
        else "Sie werden innerhalb von 3 Werktagen mit einer indikativen Einschätzung kontaktiert"
    )
    st.markdown(
        f"""
        <div class='submitted-card'>
            <div style='font-size:48px;margin-bottom:12px;'>🎉</div>
            <h2 style='margin-bottom:8px;'>Vielen Dank für Ihre Einreichung!</h2>
            <p style='color:#065F46;font-size:15px;margin:0;'>
                Wir haben Ihre Antworten erhalten — <strong>{meta['name']}</strong>
                wurde erfolgreich an unser Acquisitions-Team weitergeleitet.
            </p>
            <p style='color:#065F46;font-size:13px;margin-top:16px;'>
                Vollständigkeit: <strong>{meta['completion_pct']}%</strong> · {follow_up}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("&nbsp;")
    if meta.get("has_bwa"):
        st.info(
            "📊 **Ihre BWA-Dateien wurden übermittelt.** "
            "Unser Team wird sie automatisch analysieren.",
            icon="✅",
        )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Neuen Fragebogen starten", use_container_width=True):
            keys_to_clear = [
                k for k in st.session_state.keys()
                if k.startswith("seller_") or k.startswith("q_")
            ]
            for k in keys_to_clear:
                del st.session_state[k]
            st.rerun()
    with col2:
        if st.session_state.get("authenticated"):
            if st.button("🛩️ Zum Dashboard", type="primary", use_container_width=True):
                st.session_state["active_target_id"] = meta["target_id"]
                st.switch_page("app.py")
        else:
            if st.button("🔑 Team-Login für Dashboard", type="primary", use_container_width=True):
                st.session_state["_post_submit_target_id"] = meta["target_id"]
                st.session_state["_show_login"] = True
                st.rerun()

    with st.expander("ℹ️ Wie geht's für Sie weiter?"):
        st.markdown(
            """
            1. **Daten-Review:** Unser Acquisitions-Team prüft Ihre Antworten und meldet sich für eventuelle Rückfragen.
            2. **Indikative Einschätzung:** Innerhalb von 3-5 Werktagen erhalten Sie eine erste Bewertung.
            3. **Vertiefung:** Bei beidseitigem Interesse vereinbaren wir einen ausführlichen Termin (digital oder vor Ort).
            4. **Letter of Intent:** Im positiven Fall folgt ein indikatives Angebot.

            **Bei Fragen:** acquisitions@buena.com
            """
        )

    st.stop()


# ──────────────────────────────────────────────────────────────────────────
# Team Login Panel (shown when _show_login is True)
# ──────────────────────────────────────────────────────────────────────────
def _render_login_panel():
    """Renders the team login form. Returns True if login successful."""
    st.markdown("---")
    st.subheader("🔑 Team Login")
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Einloggen", type="primary", use_container_width=True)
        if submitted:
            if username == "abc" and password == "123":
                st.session_state["authenticated"] = True
                st.session_state["_show_login"] = False
                # If login triggered after submit, navigate to submitted target
                post_target = st.session_state.pop("_post_submit_target_id", None)
                if post_target:
                    st.session_state["active_target_id"] = post_target
                return True
            else:
                st.error("Ungültige Anmeldedaten.")
    if st.button("Abbrechen", use_container_width=True):
        st.session_state["_show_login"] = False
        st.rerun()
    return False


if st.session_state.get("_show_login"):
    _render_login_panel()
    if st.session_state.get("authenticated"):
        post_target = st.session_state.get("_post_submit_target_id")
        if post_target:
            st.session_state["active_target_id"] = post_target
        st.switch_page("app.py")
    st.stop()


# ──────────────────────────────────────────────────────────────────────────
# Hero + Team Login Button (top right)
# ──────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class='seller-hero'>
        <h1>🏠 Willkommen bei Buena</h1>
        <p>
        Vielen Dank, dass Sie sich für ein Gespräch mit uns entschieden haben.
        Mit diesem strukturierten Fragebogen lernen wir Ihr Unternehmen kennen
        und können Ihnen schnell und transparent Rückmeldung geben.
        </p>
        <p style='font-size:13px;color:#BFDBFE;margin-top:16px;'>
        ⏱️ Bearbeitungszeit ca. 30–45 Minuten · 💾 Antworten werden in dieser Sitzung gespeichert · 🔒 Vertraulich behandelt
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button("🔑 Team Login", use_container_width=True,
                help="Nur für Buena-Mitarbeiter"):
    st.session_state["_show_login"] = True
    st.rerun()

st.markdown("&nbsp;", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────
# Live Progress Bar
# ──────────────────────────────────────────────────────────────────────────
progress = calculate_progress(schema, answers)

st.markdown(
    f"""
    <div class='seller-progress-wrap'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>
            <span style='font-weight:600;font-size:14px;color:#111827;'>Ihr Fortschritt</span>
            <span style='font-size:13px;color:#6B7280;'>
                {progress['answered']} / {progress['total_visible']} Fragen beantwortet
            </span>
        </div>
        <div style='background:#F3F4F6;border-radius:4px;height:10px;overflow:hidden;'>
            <div style='background:#3B82F6;height:100%;width:{progress['pct']}%;
                 transition:width 0.3s ease;'></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────
# Table of Contents (anchor links für Quick-Nav)
# ──────────────────────────────────────────────────────────────────────────
toc_links = []
for cat in schema["categories"]:
    cat_id = cat["id"]
    icon, short_name = seller_section_display(cat)
    toc_links.append(f"<a href='#section-{cat_id}'>{icon} {short_name}</a>")

st.markdown(
    f"<div class='seller-toc'>"
    f"<strong style='color:#374151;'>Sektionen:</strong> {' '.join(toc_links)}"
    f"</div>",
    unsafe_allow_html=True,
)


# ──────────────────────────────────────────────────────────────────────────
# Question Renderer
# ──────────────────────────────────────────────────────────────────────────
def render_question(q: dict):
    """Rendert eine einzelne Frage. Speichert Wert in answers[qid]."""
    qid = q["id"]
    label = q["text"]
    if q.get("required"):
        label += " *"
    t = q["type"]

    widget_key = f"q_{qid}"
    current = answers.get(qid)

    if t == "text":
        val = st.text_input(
            label, value=current or "", key=widget_key, placeholder="Ihre Antwort…"
        )
        answers[qid] = val if val.strip() else None

    elif t == "textarea":
        val = st.text_area(
            label, value=current or "", key=widget_key, placeholder="Ihre Antwort…"
        )
        answers[qid] = val if val.strip() else None

    elif t == "number":
        val = st.number_input(
            label,
            value=current if isinstance(current, (int, float)) else None,
            min_value=q.get("min"),
            max_value=q.get("max"),
            key=widget_key,
            placeholder="z.B. 0",
        )
        answers[qid] = val

    elif t == "select":
        options = ["— bitte auswählen —"] + q.get("options", [])
        idx = 0
        if current and current in q.get("options", []):
            idx = options.index(current)
        val = st.selectbox(label, options=options, index=idx, key=widget_key)
        answers[qid] = val if val != "— bitte auswählen —" else None

    elif t == "multiselect":
        val = st.multiselect(
            label,
            options=q.get("options", []),
            default=current if isinstance(current, list) else [],
            key=widget_key,
        )
        answers[qid] = val if val else None

    elif t == "boolean":
        idx = None
        if current is True or current == "Ja":
            idx = 0
        elif current is False or current == "Nein":
            idx = 1
        val = st.radio(
            label, options=["Ja", "Nein"], horizontal=True, index=idx, key=widget_key
        )
        answers[qid] = val

    elif t == "file_upload":
        files = st.file_uploader(
            label,
            accept_multiple_files=True,
            type=["xlsx", "xlsm", "pdf", "doc", "docx"],
            key=widget_key,
        )
        if files:
            answers[qid] = [f.name for f in files]
            # For BWA question (ai_trigger = bwa_to_buena_pnl): store bytes in session_state
            if q.get("ai_trigger") == "bwa_to_buena_pnl":
                bwa_entries = []
                for f in files:
                    f.seek(0)
                    bwa_entries.append({"name": f.name, "bytes": f.read()})
                st.session_state["seller_bwa_files"] = bwa_entries
        else:
            answers[qid] = None


# ──────────────────────────────────────────────────────────────────────────
# Section Intros
# ──────────────────────────────────────────────────────────────────────────
seller_intros = {
    "company_basics": "Erzählen Sie uns ein bisschen über Ihr Unternehmen.",
    "portfolio": "Wie ist Ihr Portfolio aufgestellt? Welche Verwaltungsarten betreuen Sie?",
    "customers": "Wer sind Ihre Kunden? Wir möchten Ihre Beziehungen besser verstehen.",
    "operations": "Wie arbeiten Sie heute? Welche Tools und Prozesse sind im Einsatz?",
    "people": "Erzählen Sie uns über Ihr Team — die Menschen, die Ihr Unternehmen ausmachen.",
    "financials": "Die finanziellen Eckdaten der letzten 3 Jahre.",
    "knockouts": "Ein paar formale Fragen zu rechtlichen und Compliance-Themen.",
}

# ──────────────────────────────────────────────────────────────────────────
# Render all sections (immer offen, keine Expander)
# ──────────────────────────────────────────────────────────────────────────
for cat in schema["categories"]:
    cat_id = cat["id"]
    cat_questions = cat["questions"]

    # Anchor-Target
    st.markdown(f"<div id='section-{cat_id}'></div>", unsafe_allow_html=True)

    # Visible question count + answered count
    visible = [q for q in cat_questions if is_question_visible(q, answers)]
    answered_in_cat = sum(
        1 for q in visible if answers.get(q["id"]) not in (None, "", [])
    )

    icon, short_name = seller_section_display(cat)
    section_intro = seller_intros.get(cat_id, "")

    # Section header
    st.markdown(
        f"""
        <div class='seller-section-header'>
            <div style='display:flex;justify-content:space-between;align-items:center;'>
                <span>{icon} {short_name}</span>
                <span class='seller-section-progress'>
                    {answered_in_cat} / {len(visible)} beantwortet
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section body — Streamlit container für Form-Felder
    with st.container():
        st.markdown(
            f"<div class='seller-section-body'>"
            f"<div class='seller-section-intro'>{section_intro}</div>",
            unsafe_allow_html=True,
        )

        for q in cat_questions:
            if is_question_visible(q, answers):
                render_question(q)

        st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────
# Submit Section
# ──────────────────────────────────────────────────────────────────────────
st.markdown("---")

# Validation Display
if st.session_state.get("seller_show_validation"):
    is_valid, errors = validate_answers(schema, answers)
    if errors:
        # Filter to non-required errors for the warning section
        portfolio_err = [e for e in errors if "müssen 100% ergeben" in e]
        if portfolio_err:
            st.error("⚠️ **Fehler bei den Portfolio-Anteilen:**")
            for err in portfolio_err:
                st.markdown(f"- {err}")

# Submit Buttons
col_submit_info, col_submit_btn = st.columns([2, 1])

with col_submit_info:
    if progress["pct"] < 100:
        st.info(
            f"📋 Sie können den Fragebogen jederzeit einreichen — auch teilweise. "
            f"Bei {progress['pct']}% Vollständigkeit melden wir uns für die fehlenden Details. "
            f"Bei 100% erhalten Sie schneller eine Einschätzung."
        )

with col_submit_btn:
    # Zwischenspeichern Button (über Submit)
    if st.button(
        "💾 Zwischenspeichern",
        use_container_width=True,
        help="Antworten bleiben in dieser Session gespeichert. Sie können später fortfahren.",
    ):
        st.toast(
            f"💾 {progress['answered']} Antworten zwischengespeichert "
            f"({progress['pct']}% beantwortet)",
            icon="💾",
        )

    submit_label = (
        "✓ Fragebogen einreichen"
        if progress["pct"] >= 100
        else f"📤 Mit {progress['pct']}% einreichen"
    )

    if st.button(submit_label, type="primary", use_container_width=True):
        is_valid, errors = validate_answers(schema, answers)

        # Block only on hard structural errors (sum-check)
        hard_errors = [e for e in errors if "müssen 100% ergeben" in e]

        if hard_errors:
            st.session_state["seller_show_validation"] = True
            st.rerun()
        else:
            target = form_answers_to_target(
                answers=answers,
                schema=schema,
                target_id="",
                completion_pct=progress["pct"],
            )
            new_id = add_target(target)

            # Transfer BWA files to the new target (readable in Target Detail → P&L tab)
            bwa_files = st.session_state.get("seller_bwa_files", [])
            if bwa_files:
                st.session_state[f"bwa_for_target_{new_id}"] = bwa_files

            st.session_state["seller_submitted"] = True
            st.session_state["seller_submission_meta"] = {
                "target_id": new_id,
                "name": target["name"],
                "completion_pct": progress["pct"],
                "stage": target["status"],
                "has_bwa": bool(bwa_files),
            }
            st.rerun()


# ──────────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class='seller-footer'>
        <strong>Buena GmbH</strong> · Berlin · acquisitions@buena.com<br>
        Ihre Daten werden vertraulich behandelt und nicht an Dritte weitergegeben.
    </div>
    """,
    unsafe_allow_html=True,
)

