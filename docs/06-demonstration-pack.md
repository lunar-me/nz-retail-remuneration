# Demonstration Pack

This document provides a walkthrough of the complete NZ Retail Remuneration &
Workforce Programme, from synthetic data generation to the integrated
scorecard.

## Overview

The programme demonstrates subject-matter expertise across:

1. **Leave entitlement & accrual** (NZ Holidays Act 2003 concepts)
2. **Flexible remuneration costing** (fully-loaded packages, scenario modelling)
3. **Demand → capacity planning** (labour requirements, gap analysis)
4. **Integrated scorecard & alerting** (single health view)

All built on a **fully synthetic**, reproducible dataset — no real employee
data is used.

## Demonstration Walkthrough

### Step 1: Generate the Synthetic Data

```bash
python scripts/generate_synthetic_data.py
```

Produces 8 versioned tables in `data/synthetic/v1/`:

- 12 NZ retail stores
- 650 employees (28% full-time, 47% part-time, 25% casual)
- 122,209 leave transactions
- 180,940 roster shifts
- 8,760 daily demand records
- Remuneration components, leave types, NZ calendar

### Step 2: Leave Entitlement & Accrual

```bash
python scripts/run_leave_engine.py --as-of 2026-06-30 --explain
```

Computes:

- Current annual/sick leave balances for all employees
- Eligibility checks (12-month annual leave vesting, 6-month sick)
- Pro-rated accruals for part-time/casual staff
- Human-readable balance explanations

### Step 3: Remuneration Costing & Scenarios

```bash
python scripts/run_costing_scenarios.py
```

Computes:

- Fully-loaded hourly costs (base + KiwiSaver + leave + insurance + flexibility)
- Total annual cost: **$23.2M** for 650 employees
- 7 what-if scenarios (extra leave days, higher insurance, KiwiSaver, etc.)
- Cost impact per scenario in $ and %

### Step 4: Capacity Planning

```bash
python scripts/run_capacity_plan.py
```

Computes:

- Required labour hours from demand (via productivity standards)
- Available hours after leave (using rosters)
- Capacity gaps per store-day-role
- Roster suggestions respecting flexibility preferences

### Step 5: Integrated Scorecard

```bash
python scripts/run_scorecard.py --as-of 2026-06-30
```

Produces:

- Programme health metrics (leave liability, insurance, flexibility, cost)
- 12 store-level scorecards
- Exception alerts (capacity, insurance, flexibility)
- Overall health rating

### Full Demonstration

```bash
python scripts/run_full_demo.py
```

Runs all 5 steps in sequence and writes demonstration outputs.

## Key Demonstration Outputs

| Output | Location | What it shows |
| -------- | ---------- | --------------- |
| Synthetic data | `data/synthetic/v1/` | 8 versioned tables |
| Leave balances | `outputs/leave_balances/` | Balances + projections + explanations |
| Cost summary | `outputs/costing_scenarios/` | Fully-loaded costs + scenario comparison |
| Capacity gaps | `outputs/capacity_reports/` | Gaps + suggestions + store summaries |
| Scorecard | `outputs/scorecards/` | Health metrics + alerts + report |
| Demo pack | `outputs/demo/` | Combined demonstration outputs |

## Test Coverage

```bash
python -m pytest
```

- **65 unit tests** — all engine calculations verified
- **7 integration tests** — full chain verified on synthetic data

## Success Metrics

1. **Leave liability** is visible and controlled (avg annual balance < 30 days)
2. **Package cost** is transparent ($23.2M, 86.7% base pay)
3. **Scenario impact** is quantifiable before promises are made
4. **Capacity gaps** are flagged before they become service issues
5. **One scorecard** shows both reward and workforce health
