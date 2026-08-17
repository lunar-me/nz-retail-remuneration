# Architecture Overview

## Programme Structure

```
nz-retail-remuneration/
├── data/synthetic/v1/     # Versioned synthetic dataset (8 tables)
├── src/
│   ├── common/            # Shared utilities (config, calendar, validation, io)
│   ├── synthetic_data/    # Project 0: Synthetic data generators
│   ├── leave_engine/      # Project 1: Leave Entitlement & Accrual
│   ├── remuneration/      # Project 2: Remuneration Costing & Scenarios
│   ├── capacity/          # Project 3: Demand → Capacity Planner
│   └── scorecard/         # Project 4: Integrated Scorecard & Alerting
├── configs/               # YAML configuration for all engines
├── scripts/               # CLI entry points
├── tests/                 # Unit + integration tests
├── docs/                  # Design documentation
└── outputs/               # Generated reports
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SYNTHETIC DATA LAYER                     │
│  data/synthetic/v1/ (stores, employees, leave, rosters,     │
│  demand, remuneration, calendar — 8 tables, versioned)      │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┼────────────┬──────────────┐
              ▼            ▼            ▼              ▼
        ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐
        │  LEAVE    │ │ REMUNERA- │ │ CAPACITY  │ │  SCORECARD   │
        │  ENGINE   │ │  TION     │ │  PLANNER  │ │  & ALERTING  │
        │           │ │  COSTING  │ │           │ │              │
        │ Balances, │ │ Fully-    │ │ Required   │ │ Combines all │
        │ accruals, │ │ loaded    │ │ vs avail   │ │ engines:     │
        │ eligibility│ │ costs,   │ │ hours,    │ │ health,      │
        │ OWP/AWE   │ │ scenarios │ │ gaps,     │ │ alerts       │
        └───────────┘ └───────────┘ └───────────┘ └──────────────┘
```

## Engine Dependencies

| Engine | Consumes | Produces |
|--------|----------|----------|
| Leave | employees, leave_types, leave_transactions | Balance summaries, explanations |
| Remuneration | employees, remuneration_components | Cost summaries, scenario comparisons |
| Capacity | employees, stores, leave, demand, rosters, calendar | Required hours, gaps, suggestions |
| Scorecard | All engines' outputs | Health metrics, alerts, scorecard |

## Configuration

All assumptions live in YAML files under `configs/`:

| Config | Purpose |
|--------|---------|
| `synthetic_data.yaml` | Generation parameters (seed, volumes, patterns) |
| `leave_rules.yaml` | Holidays Act rules (accrual rates, vesting) |
| `costing_assumptions.yaml` | Cost rates (KiwiSaver, leave loading, insurance) |

## CLI Entry Points

```bash
# Generate synthetic data
python scripts/generate_synthetic_data.py

# Leave engine
python scripts/run_leave_engine.py [--as-of DATE] [--employees IDS] [--explain]

# Remuneration costing
python scripts/run_costing_scenarios.py [--scenarios NAMES]

# Capacity planner
python scripts/run_capacity_plan.py [--start DATE] [--end DATE] [--stores IDS]

# Scorecard
python scripts/run_scorecard.py [--as-of DATE]

# Full demonstration chain
python scripts/run_full_demo.py
```

## Testing

```bash
# Unit tests
python -m pytest tests/unit

# Integration tests (requires synthetic data)
python -m pytest tests/integration

# All tests
python -m pytest
```

## Reproducibility

- All synthetic data is generated with a fixed seed (`42`)
- Running any engine against the same synthetic version produces identical results
- Data is versioned at `data/synthetic/v1/` with `_manifest.json` metadata