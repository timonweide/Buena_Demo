# 🛩️ Buena Piloto

> Acquisition & Integration Cockpit for Buena's PMI Lead role.
> Take-Home submission by Timon Weidemann · April / May 2026.

A Streamlit-based prototype that productizes Buena's acquisition + post-merger integration workflow — pipeline-driven, with stage-gated access controls between Outreach → DD → Offer Accepted.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Architecture: Internal vs. Seller Split

**Two distinct user experiences:**

### 🛩️ Internal Dashboard (`app.py` + `pages/1-3`)
For the Buena PMI / M&A team. Pipeline-driven, full information visibility, score / flag / KO-aware, can move targets between stages.

### 👤 Seller Portal (`pages/4_Seller_Portal.py`)
For the seller of an acquisition target. Friendly tone, no internal flags, no knock-out labels, progress bar prominent. In production: token-URL access (`buena.com/intake?token=…`).

---

## Pipeline Stages

| Stage | Page Access |
|---|---|
| 📨 **Outreach** | Target Detail (Seller füllt Intake-Form parallel) |
| 🔍 **DD** | + LBO Model |
| 🤝 **Offer Accepted** | + PMI Playbook |

Locked pages zeigen einen Stage-Gate-Screen mit klarem Hinweis welche Stage erforderlich ist und wie man dorthin kommt.

---

## Project Structure

```
buena_piloto/
├── app.py                              # Internal Dashboard: Kanban + Active Target Cockpit
├── pages/
│   ├── 1_📊_Target_Detail.py           # Always available
│   ├── 2_💰_LBO_Model.py               # Locked unless DD+
│   ├── 3_🛠️_PMI_Playbook.py            # Locked unless Offer Accepted
│   └── 4_👤_Seller_Portal.py           # Seller-facing intake (no sidebar)
├── data/
│   ├── targets.json                    # 3 mock targets (alle 3 Stages abgedeckt)
│   ├── dd_schema.json                  # ~58 DD questions across 7 categories
│   └── pmi_tasks_template.json         # 3 workstreams × 6-7 tasks
├── lib/
│   ├── data_loader.py                  # JSON → session_state (mutable for stage transitions)
│   ├── pipeline.py                     # Stage definitions + access control + transitions
│   ├── scoring.py                      # 4-dim weighted scoring (Tag 4 fills logic)
│   └── lbo_engine.py                   # Stub (Tag 5 fills full model)
├── requirements.txt
└── README.md
```

---

## 7-Day Build Roadmap

| Day | Output | Status |
|---|---|---|
| 1 | DD-Liste, Buena P&L Schema, Scoring-Logik, LBO-Specs, PMI-Struktur | ✅ |
| 2a | Streamlit-Skeleton, 5 Pages, Mock-Daten 3 Targets, Datenmodell | ✅ |
| **2b** | **Pipeline-driven Architecture: Internal/Seller Split + Stage Gates** | **✅** |
| 3 | Seller Portal voll funktional (Auto-Form-Renderer, Conditional Logic, Submit Flow) | ⏳ |
| 4 | Scoring engine mit editable weights + Sub-Score-Drill-Down | ⏳ |
| 5 | AI Parser (BWA → Buena P&L via Claude API) + LBO mit Earn-Out + Sensitivity | ⏳ |
| 6 | State-Persistence via SQLite + PMI Auto-Plan-Generation aus DD | ⏳ |
| 7 | Loom Walkthrough + Cover Memo + Bug Fixes + Streamlit Cloud Deployment | ⏳ |

---

## Mock Targets (zum Demo-Test)

| Target | Stage | Profile | Score | Demo-Zweck |
|---|---|---|---|---|
| **NordImmo Verwaltung** (Hamburg) | Outreach (65% Intake) | Excel-only Tech, sub-scale | 45 | LBO + PMI **locked** |
| **Hausverwaltung Müller GmbH** (München) | DD | Sweet-Spot, Nachfolge-Trigger | 73 | LBO **unlocked**, PMI locked |
| **Berliner Immobilien Service** (Berlin) | Offer Accepted | Top-3 = 45% Konzentration | 67 | Alles **unlocked** |

---

## Demo-Flow (für Loom)

1. Land on **Internal Dashboard** → see 3-column Kanban
2. Click NordImmo card → "Set as active" → Active Cockpit zeigt Outreach-Status mit Intake-Progress
3. Try to open LBO Model from sidebar → **Lock-Screen** mit Hinweis "Required: DD"
4. Switch to Müller (already in DD) → LBO funktioniert, PMI locked
5. Click "Mark as Offer Accepted" → Stage-Transition → PMI unlocked
6. Open PMI Playbook → 18 Tasks across 3 Workstreams, Owner-Selectbox, Status-Tracking
7. Switch to **Seller Portal** → "Hier sieht der Verkäufer das Tool" — friendly, no flags

---

## Design Principles

1. **What can be calculated, isn't asked** — abgeleitete Metriken (Units/PM, EBITDA-Marge, AR%) immer im Admin-Panel berechnet.
2. **Schema-driven, not hard-coded** — DD-Form aus `dd_schema.json`; Felder ändern = JSON ändern.
3. **Editable everything** — Scoring-Gewichte, LBO-Inputs, PMI-Owners. Linus muss live priorisieren können.
4. **Stage-driven UX** — Pages werden gated by Pipeline-Stage. Kein "wir machen schon mal LBO bevor DD-Daten da sind".
5. **Audience-aware UI** — Seller sieht keine Flags / Knock-Out-Labels, Linus sieht alles.
6. **Honesty about state** — Stubs werden klar markiert (`_stub: true`); kein Fake-Polish.

---

## License & Notes

Built for Buena Take-Home — not for production use. Mock data only.
