# NZ Retail Workforce — Streamlit Visualisation App

This Streamlit application **visualises the pre-calculated outputs** of the
NZ Retail Remuneration & Workforce Programme. It does **not** run any engines
or calculations — it loads the pre-computed artifacts from `data/synthetic/v1/`
and `outputs/` and presents them in an interactive dashboard.

## Quick Start

```bash
# From the project root
streamlit run app/app.py
```

Then open your browser to the URL shown (typically `http://localhost:8501`).

## Sections

| Section | What It Shows |
|---------|---------------|
| **Overview** | Project intro, engine summaries, architecture diagram, key principles |
| **Synthetic Data** | The 8 data tables, employee demographics, demand patterns, roster activity, store network |
| **Leave Engine** | Current balances, leave type rules, projections, explanations |
| **Remuneration** | Cost breakdown by component, costs by role/type/store, scenario modelling |
| **Capacity Planner** | Gap analysis with filters, capacity status by store, roster suggestions |
| **Scorecard** | Programme health metrics, store scorecards, exception alerts |

## Data Sources

All data is loaded from pre-computed files:

- **Synthetic data**: `data/synthetic/v1/*.csv`
- **Leave engine**: `outputs/leave_balances/*`
- **Remuneration**: `outputs/costing_scenarios/*`
- **Capacity**: `outputs/capacity_reports/*`
- **Scorecard**: `outputs/scorecards/*`

## Requirements

- `streamlit`
- `pandas`
- `plotly`

Install with:

```bash
pip install streamlit plotly pandas
```

## Architecture

```
app/
├── app.py     # Main Streamlit application with all pages
└── utils.py   # Data loading and derived-data helpers
```

The app uses `@st.cache_data` decorators to load CSVs once and cache them
across reruns for performance.