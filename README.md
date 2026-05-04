# Buena Piloto

**Acquisition & Integration Cockpit** — Take-Home Submission für die Buena Bewerbung.
Von Timon Weidemann - Mai 2026.

Ein produktionsnaher Streamlit-Prototyp der Buenas Akquisitions- und Post-Merger-Integrations-Workflow abbildet: von der Datenerfassung des Verkäufers über Due Diligence und LBO-Modellierung bis zum PMI-Playbook. Dieses Produkt soll dafür sorgen, dass Akquisitionen möglichst effizient durchgeführt werden können, indem Datenflüsse und Prozesse optimiert werden. Die Erkenntnisse basieren auf Erfahrungen aus mittelständischen Akquisitionen und hoch skalierten E-Commerce Akquisitionsprozessen.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Öffnet auf `http://localhost:8501` — direkt auf dem Seller Portal.

**Anthropic API Key (optional, für Claude-Parsing und AI Executive Summary):**

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
streamlit run app.py
```

Ohne Key laufen der BWA-Parser und die IC-Memo-Executive-Summary im deterministischen Mock-Mode.

---

## Architektur

Das Tool hat zwei klar getrennte Nutzererfahrungen:

### Seller Portal (`pages/4_👤_Seller_Portal.py`)
Die Landing Page der App. Für Verkäufer einer Hausverwaltung. Schema-getriebenes DD-Formular mit 75 Fragen in 7 Kategorien, Conditional Logic, Live-Progress-Bar und Datei-Upload für BWA/GuV. Keine internen Buena-Begriffe, kein Knock-Out-Labeling. Submit erstellt automatisch ein neues Target im internen Dashboard.

### Internes Dashboard (`app.py` + `pages/1-3`)
Zugang via Mock-Login (`abc` / `123`). Für das Buena-Acquisitions-Team. Pipeline-getrieben mit Stage-Gating: Seiten werden erst freigeschaltet wenn die notwendige Stage erreicht ist. Alle Daten des Verkäufers werden intern zur Analyse aufbereitet.

---

## Pipeline-Stages und Page-Gating

| Stage | Freigeschaltete Pages |
|---|---|
| 📨 **Outreach** | Target Detail |
| 🔍 **DD** | + LBO Model |
| 🤝 **Offer Accepted** | + PMI Playbook |

Gesperrte Pages zeigen einen Stage-Gate-Screen mit Hinweis welche Stage erforderlich ist.

---

## Features

### Seller Portal
- Schema-getriebenes Formular aus `dd_schema.json` — Felder ändern = JSON ändern, kein Code
- 7 Conditional-Logic-Regeln (z.B. Folgefragen bei mehreren Gesellschaftern oder Schlüsselperson-Risiko)
- Validerung: Portfolio-Anteile müssen 100% ergeben, Pflichtfelder werden geprüft
- BWA-Upload (Excel und PDF) wird automatisch ins Target Detail der entsprechenden Ziel-Pipeline übertragen
- Submit ohne 100% Vollständigkeit möglich — Target landet als *Outreach* mit Completion-Prozentsatz

### Dashboard
#### Overview
- Auswahl verschiedener Targets
- Überblick der wichtigsten KPIs des aktuellen Targets - basierend auf der aktuellen Stage
- Darstellung der Pipeline in einem Kanban-Board
#### IC Memo Export (PDF)
- Buena-Branded Design: Quatrefoil-Logo, Helvetica, schwarz/weiß, minimalistisch
- AI-generierte Executive Summary via Claude API (Fallback: strukturiertes Template)
- Stage-aware: Outreach ohne LBO/PMI, DD mit LBO, Offer Accepted mit vollem PMI-Plan
- Sektionen: Executive Summary, Company Profile, Investment Thesis, Risk Analysis, Financial Profile, LBO Returns, PMI Plan Summary, Recommendation

### Target Detail
#### Scoring Engine
- 4 Dimensionen: Strategic Fit, Financial Health, Integration Complexity, Synergy Potential
- 14 Sub-Scores, jeder deterministisch aus DD-Daten berechnet
- Jeder Sub-Score hat eine nachvollziehbare Begründung und die Source-Question-ID
- Editable Top-Level-Weights über Sidebar-Slider, Scores updaten überall live
- Side-by-Side-Vergleich von 2–3 Targets mit Spider-Chart-Overlay
- Alle Scores und Flags werden live aus den Target-Daten berechnet
#### Flags
- Live aus Target-Daten berechnet (nicht im JSON gespeichert)
- Sortiert nach Schwere: Red → Yellow → Green
- Automatischer Knock-Out-Banner wenn kritische DD-Kriterien positiv beantwortet wurden
#### AI-Parser (BWA → Buena P&L)
- Dual-Mode: echter Claude API Call wenn `ANTHROPIC_API_KEY` gesetzt, sonst deterministischer Mock
- Unterstützt Excel (.xlsx) und PDF Formate
- Vom Seller im Portal hochgeladene BWA wird automatisch importiert
- 21 standardisierte Buena-P&L-Kategorien, jede Mapping-Entscheidung mit Confidence-Score (0–100%)
- Stellt Vergleichbarkeit zwischen Target Assets her
- Filter "Nur Confidence < 70%" für fokussierte manuelle Review
- Manueller Override per Selectbox für jede Zeile
- Aggregiertes Buena Standard P&L als klassische GuV mit aufklappbaren Detail-Buckets und Margen
- Vergleich Self-Reported (DD) vs. AI-parsed (BWA) mit Δ-Spalte und Warnung bei >20% Abweichung
- Approved P&L wird im LBO Model als alternative Datenquelle angeboten

### LBO Model
- Year-by-Year Projektion für 3–20 Jahre (indikativ, da Buena Long-Term-Hold Model verfolgt)
- Synergien hinzufügen in drei Phasen: Y1, Y2, Run-Rate ab Y3
- Earn-Out mit Threshold-basiertem Trigger — finanziert aus FCF oder neuem Equity
- Debt Schedule: Mandatory Amortization + Cash Sweep
- Equity Value Bridge als Plotly Wasserfall: EBITDA-Wachstum, Multiple Arbitrage, Schuldentilgung
- Settings werden pro Target und Session in `session_state` gespeichert
- Toggle: AI-parsed BWA-Werte vs. Self-Reported-DD Werte als Basis

### PMI Playbook
- 3 Workstreams x 19 Base-Tasks mit Owner-Selektion, Status-Tracking, eigenen Notizen
- **Auto-Plan-Generation:** 7 DD-Regeln passen das Playbook basierend auf den Verkäufer DD Antworten dynamisch an:
  - Excel/Word-Stack → zusätzliche Datenrekonstruktion-Tasks
  - On-Prem-Deployment → physischer Server-Zugang als Day-1-Task
  - Schlüsselperson-Risiko → Bindungs-Task auf Day 1–7 priorisiert + Earn-Out-Task neu
  - Customer-Konzentration > 35% → Top-Customer-Tour vorgezogen + Vertragsverlängerung-Task neu
  - Übergangsperiode < 3 Monate → Knowledge-Transfer-Sprint komprimiert
  - >30% Mitarbeiter über 60J → Wissens-Transfer-Programm neu
  - Komplexe Eigentümerstruktur → WEG-Beirats-Konsens-Task neu
- Auto-generierte und auto-modifizierte Tasks sind transparent mit `[AUTO]` markiert
- Toggle zwischen Basis-Playbook und Auto-Plan mit Expander der angewendeten Regeln

---

## Projektstruktur

```
buena_piloto/
├── app.py                       # Router (Auth-Gate) + Internal Dashboard (Kanban, Cockpit)
├── build_demo_bwa.py            # Generiert demo_bwa_mueller.xlsx (einmalig ausführen)
│
├── pages/
│   ├── 1_📊_Target_Detail.py   # Scoring, Flags, AI-Parser P&L, Comparison — Stage: alle
│   ├── 2_💰_LBO_Model.py       # Year-by-Year LBO, Earn-Out, Waterfall — Stage: DD+
│   ├── 3_🛠️_PMI_Playbook.py   # Auto-Plan, Task-Tracking — Stage: Offer Accepted
│   └── 4_👤_Seller_Portal.py   # Seller-facing DD-Intake, Login-Gate
│
├── lib/
│   ├── ai_parser.py             # BWA → Buena P&L (Claude API + Mock, Excel + PDF)
│   ├── data_loader.py           # targets.json → session_state, add_target(), derived metrics
│   ├── form_engine.py           # Conditional Logic, Validation, Form → Target Mapping
│   ├── ic_memo.py               # Buena-styled IC Memo PDF (Buena Logo, Executive Summary)
│   ├── lbo_engine.py            # Year-by-Year FCF, Debt Schedule, IRR/MoM
│   ├── pipeline.py              # Stage-Definitionen, Access-Control, Transitions
│   ├── pmi_auto.py              # 7 Auto-Plan-Regeln, generate_auto_plan()
│   └── scoring.py               # 4 Dimensionen x 14 Sub-Scores, Live-Flags
│
└── data/
    ├── buena_logo.png           # Quatrefoil-Logo für IC Memo
    ├── dd_schema.json           # 75 DD-Fragen in 7 Kategorien (inkl. Conditional Logic)
    ├── pmi_tasks_template.json  # 3 Workstreams x 19 Base-Tasks
    ├── targets.json             # 3 Mock-Targets (Outreach, DD, Offer Accepted)
    └── demo_files/
        └── demo_bwa_mueller.xlsx  # Realistische DATEV-SKR04-BWA für Demo
```

---

## Mock-Targets

| Target | Stage | Profil | Score |
|---|---|---|---|
| **NordImmo Verwaltung** (Hamburg) | Outreach, 65% Intake | Excel/Word-Stack, 1.200 Units, kurze Übergangsperiode | 57 |
| **Hausverwaltung Müller GmbH** (München) | DD | Sweet-Spot 2.800 Units, Nachfolge-Trigger, niedrige Marge | 82 |
| **Berliner Immobilien Service GmbH** (Berlin) | Offer Accepted | 5.200 Units, Top-3 = 45%, Schlüsselperson-Risiko, On-Prem | 63 |

Scores werden live berechnet — keine statischen Werte im JSON.

---

## Design-Prinzipien

**Was berechnet werden kann, wird nicht abgefragt.** Abgeleitete Metriken (Units/PM, EBITDA-Marge, Revenue CAGR, AR%-Umsatz) werden automatisch berechnet und im Dashboard angezeigt — der Seller füllt nur Roh-Werte aus und hat somit weniger Aufwand.

**Schema-getrieben, nicht hardcoded.** DD-Fragen, PMI-Tasks und Auto-Plan-Regeln liegen in JSON/Python-Datenstrukturen. Neue Fragen, Tasks oder Risiko-Regeln hinzufügen bedeutet JSON oder eine Funktion ergänzen — kein UI-Code anfassen.

**Stage-getriebene UX.** Kein LBO ohne DD-Daten. Kein PMI ohne Offer. Pages werden durch Pipeline-Stage freigeschaltet, nicht durch manuelle Entscheidungen.

**Audience-aware.** Seller sieht keine internen Begriffe, keine Flags, keine Scores. Das interne Team sieht alles. Gleiche Datenbasis, zwei verschiedene Interfaces.

**Transparent über Grenzen.** Persistenz läuft über `session_state` — stirbt mit dem Browser-Tab. Production würde SQLite oder Postgres brauchen. Die Scoring-Gewichte und Auto-Plan-Regeln sind aus Recherche kalibriert, nicht aus Buena-Realität. Das Tool ist darauf ausgelegt, mit echten Daten zu lernen.

---

## Known Limitations

- **Keine DB-Persistenz.** Alle Daten (Stage-Transitions, LBO-Inputs, PMI-Status, Scoring-Gewichte) liegen im Streamlit-`session_state` und werden beim Schließen des Tabs zurückgesetzt. Migration auf SQLite oder ähnliches müsste vor Production passieren.
- **PDF-Parsing nur für text-basierte PDFs.** Gescannte PDFs ohne eingebetteten Text werden nicht erkannt.
- **Kein Token-URL-Schutz für das Seller Portal.** In Production würde jede Seller-Session über einen einmaligen Token-Link (`buena.com/intake?token=…`) aufgerufen.
- **Mock-Login.** `abc` / `123` ist ein Demo-Credential. Production: SSO oder OAuth mit Buena Mitarbeiter Google Konto.

---

*Built for Buena Demo — not for production use.*
