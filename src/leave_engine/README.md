# Leave Entitlement & Accrual Engine

Implements NZ Holidays Act-oriented leave accrual, balance tracking, and
explanation logic over the synthetic data layer.

## Overview

The leave engine provides:

- **Accrual calculation** — weekly pro-rated accruals for annual, sick, and
  bereavement leave based on contracted hours
- **Eligibility rules** — Holidays Act concepts (12-month annual leave vesting,
  6-month sick/bereavement eligibility)
- **Balance tracking** — replay of synthetic transaction history to compute
  current balances
- **Projections** — future balance projections with cap handling
- **Explanations** — human-readable reports for auditability
- **Pay method flags** — ordinary weekly pay / average weekly earnings
  (simplified)

## Module Structure

```
src/leave_engine/
├── __init__.py        # Public exports
├── models.py          # Typed data models (LeaveType, Employee, LeaveBalance)
├── holidays_act.py    # NZ Holidays Act 2003 rules (simplified but explicit)
├── accrual.py         # Core accrual & balance engine
└── balance.py         # Balance calculator, projections, explanations
```

## Usage

### From the CLI

```bash
# Compute current balances and projections
python scripts/run_leave_engine.py

# Specific as-of date
python scripts/run_leave_engine.py --as-of 2026-06-30

# Specific employees + explanation reports
python scripts/run_leave_engine.py --employees 1,2,3 --explain

# 26-week projection
python scripts/run_leave_engine.py --weeks-ahead 26
```

### From Python

```python
import datetime as dt
from src.leave_engine import LeaveAccrualEngine, LeaveBalanceCalculator, HolidaysActRules
from src.common.config import load_yaml
from src.common.io import load_dataset

# Load data & rules
tables = load_dataset("data/synthetic/v1")
rules = HolidaysActRules(load_yaml("leave_rules.yaml"))

# Compute balances
as_of = dt.date(2026, 6, 30)
calculator = LeaveBalanceCalculator(as_of=as_of)
summary = calculator.current_balances_summary(
    tables["employees"],
    tables["leave_types"],
    tables["leave_transactions"],
)

# Generate explanations
explanations = calculator.explain_balances(
    tables["employees"],
    tables["leave_types"],
    tables["leave_transactions"],
    employee_ids=[1, 2, 3],
)
print(calculator.render_explanations_to_text(explanations))
```

## Key Rules (Holidays Act 2003, simplified)

| Rule | Value |
|------|-------|
| Annual leave | 4 weeks/year after 12 months continuous employment |
| Sick leave | 10 days/year after 6 months |
| Bereavement | 3 days/year after 6 months |
| Annual cap | 8 weeks (configurable) |
| Sick cap | 20 days (configurable) |
| Pay method | OWP for FT/PT, AWE for casual (simplified) |

## Configuration

Rules live in `configs/leave_rules.yaml`:

- `hours_per_week` / `hours_per_day` — standard working pattern
- `annual_leave.weeks_per_year` — statutory 4 weeks
- `annual_leave.vesting_months` — 12 months eligibility
- `annual_leave.max_balance_weeks` — 8-week cap
- `sick_leave.days_per_year` — 10 days
- `sick_leave.max_balance_days` — 20-day cap
- `ordinary_weekly_pay_method` — pay calculation flag

## Edge Cases Handled

- **Long-tenure staff** — high annual leave balances (capped at 8 weeks)
- **New starters** — no accrual history; computed from start date with
  vesting eligibility checks
- **Casual workers** — pro-rated accrual based on contracted hours, AWE pay
  method
- **Part-time workers** — pro-rated accrual, OWP pay method

## Outputs

The CLI writes to `outputs/leave_balances/`:

- `current_balances.csv` — one row per employee per leave code
- `balance_projections.csv` — projected balances N weeks ahead
- `balance_explanations.txt` — readable explanations (with `--explain`)