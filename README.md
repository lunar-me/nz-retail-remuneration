# NZ Retail Remuneration & Workforce Programme

Synthetic-data-driven models and calculation engines for remuneration schemes, leave management, and workforce capacity planning in a New Zealand retail environment.

> **Annotation:** A privacy-first, NZ retail workforce programme built entirely on synthetic data. It delivers auditable leave entitlements aligned to the Holidays Act 2003, transparent remuneration costing with what-if scenarios, demand-driven capacity planning, and an integrated scorecard — all reproducible via fixed seeds and versioned datasets.

## Overview

This repository delivers a complete, privacy-safe, data-driven workforce programme built entirely on **synthetic data**. It provides:

- **Accurate, auditable leave entitlements** — NZ Holidays Act 2003-oriented accrual and balance engine
- **Transparent remuneration costing** — fully-loaded costs with what-if scenario modelling
- **Demand-driven capacity planning** — required vs available hours with gap analysis
- **Integrated scorecard & alerts** — one view of reward + workforce health

**No real employee or commercial data is used.** All data is generated from configurable rules with a fixed random seed.

## Quick Start

```bash
# 1. Create & activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate the synthetic data layer
python scripts/generate_synthetic_data.py

# 4. Run the full demonstration chain
python scripts/run_full_demo.py
```

## Engine Summary

| # | Engine | CLI | Description |
| --- | -------- | ----- | ------------- |
| 0 | **Synthetic Data Layer** | `scripts/generate_synthetic_data.py` | 8 versioned NZ retail tables (650 employees, 12 stores) |
| 1 | **Leave Engine** | `scripts/run_leave_engine.py` | Holidays Act accruals, balances, projections, explanations |
| 2 | **Remuneration Costing** | `scripts/run_costing_scenarios.py` | Fully-loaded costs, scenario modelling (7 default scenarios) |
| 3 | **Capacity Planner** | `scripts/run_capacity_plan.py` | Demand → labour requirements, gap analysis, roster suggestions |
| 4 | **Scorecard & Alerting** | `scripts/run_scorecard.py` | Integrated health view, exception alerts |

## Individual Engine Usage

### Leave Entitlement & Accrual Engine

```bash
# Current balances + 52-week projections
python scripts/run_leave_engine.py

# As-of a specific date + explanation reports
python scripts/run_leave_engine.py --as-of 2026-06-30 --explain
```

### Flexible Remuneration Costing

```bash
# Run all default scenarios
python scripts/run_costing_scenarios.py

# Specific scenarios
python scripts/run_costing_scenarios.py --scenarios "Baseline,+2 Days Annual Leave"
```

### Demand → Capacity Planner

```bash
# June 2026 capacity analysis
python scripts/run_capacity_plan.py

# Specific period / stores
python scripts/run_capacity_plan.py --start 2026-01-01 --end 2026-01-07 --stores 1,2,3
```

### Integrated Scorecard

```bash
python scripts/run_scorecard.py --as-of 2026-06-30
```

## Repository Structure

```text
├── data/synthetic/v1/     # Versioned synthetic dataset (8 tables)
├── src/
│   ├── common/            # Shared utilities
│   ├── synthetic_data/    # Project 0: Data generators
│   ├── leave_engine/      # Project 1: Leave engine
│   ├── remuneration/      # Project 2: Costing & scenarios
│   ├── capacity/          # Project 3: Capacity planner
│   └── scorecard/         # Project 4: Scorecard & alerts
├── configs/               # YAML configuration
├── scripts/               # CLI entry points
├── tests/                 # Unit + integration tests
├── docs/                  # Design documentation
└── outputs/               # Generated reports
```

## Configuration

All assumptions live in `configs/`:

| File | Purpose |
| ------ | --------- |
| `synthetic_data.yaml` | Generation parameters (seed, volumes, patterns) |
| `leave_rules.yaml` | Holidays Act rules (accrual rates, vesting) |
| `costing_assumptions.yaml` | Cost rates (KiwiSaver, leave loading, insurance) |

## Testing

```bash
# Run all tests (unit + integration)
python -m pytest

# Unit tests only
python -m pytest tests/unit

# Integration tests only (requires synthetic data)
python -m pytest tests/integration
```

**65 unit tests + 7 integration tests** covering all engines.

## Documentation

See `docs/` for design documents:

- `01-synthetic-data-design.md` — Synthetic data layer design
- `02-leave-engine.md` — Leave engine design
- `03-remuneration-costing.md` — Costing & scenario design
- `04-capacity-planner.md` — Capacity planner design
- `05-scorecard.md` — Scorecard & alerting design
- `06-demonstration-pack.md` — Demonstration pack walkthrough
- `architecture.md` — Full programme architecture

## Key Principles

- **Privacy first** — only synthetic data is used
- **Calculation logic over dashboards** — models and engines are the primary deliverables
- **NZ retail context** — leave rules, employment mixes, demand patterns, calendar tailored to NZ
- **Reproducibility** — fixed seeds and versioned synthetic datasets
- **Transparency** — every major assumption is documented and configurable

## Licence

This project is licensed under the [MIT License](LICENSE).
