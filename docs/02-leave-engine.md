# Leave Entitlement & Accrual Engine — Design Document

## 1. Purpose

The Leave Entitlement & Accrual Engine is the compliance-critical foundation
for leave balance management in the NZ retail environment. It provides
trusted, auditable leave balances that respect NZ Holidays Act 2003 concepts
and handle different employment types (full-time, part-time, casual).

The engine operates on the **synthetic data layer** — no real employee data
is used. All balances, accruals, and projections are computed from the
versioned synthetic tables.

## 2. Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Holidays Act oriented** | Statutory rules encoded explicitly and configurable |
| **Transparent & auditable** | Every calculation is explainable line-by-line |
| **Employment-type aware** | Pro-rating for part-time/casual, vesting checks |
| **Synthetic-data driven** | Operates on versioned `data/synthetic/v1` |
| **Edge-case tested** | Deliberate stress tests (high balances, new starters) |
| **Extensible** | Rules in YAML config; typed models; clean interfaces |

## 3. Core Rules (Holidays Act 2003, Simplified)

### 3.1 Annual Leave

- **Entitlement**: 4 weeks per year after 12 months of continuous employment
- **Accrual**: Weekly pro-rated by contracted hours:
  `(4 weeks × 40h) / 52 weeks × (contracted_hours / 40)`
- **Balance cap**: 8 weeks (configurable)
- **Pay method**: Ordinary Weekly Pay (OWP) — simplified to
  "average of last 4 weeks" flag

### 3.2 Sick Leave

- **Entitlement**: 10 days per year after 6 months of continuous employment
- **Accrual**: Weekly pro-rated by contracted hours:
  `(10 days × 8h) / 52 weeks × (contracted_hours / 40)`
- **Balance cap**: 20 days (configurable)
- **Pay method**: OWP for FT/PT, Average Weekly Earnings (AWE) for casual

### 3.3 Bereavement Leave

- **Entitlement**: 3 days per year after 6 months of continuous employment
- **Accrual**: Weekly pro-rated (rarely used; typically event-driven)

### 3.4 Pay Calculation Methods (Simplified Flags)

| Method | Applies To | Description |
|--------|------------|-------------|
| Ordinary Weekly Pay (OWP) | Full-time, Part-time | Usual weekly earnings including regular allowances |
| Average Weekly Earnings (AWE) | Casual, variable-hours | Average gross earnings over prior 52 weeks |
| Relevant Daily Pay | Public holidays | What the employee would have earned that day |

## 4. Module Architecture

```
src/leave_engine/
├── __init__.py
├── models.py          # LeaveType, Employee, LeaveBalance, LeaveTransaction
├── holidays_act.py    # HolidaysActRules: eligibility, accrual, pay methods
├── accrual.py         # LeaveAccrualEngine: transaction replay, balance calc
└── balance.py         # LeaveBalanceCalculator: summary, projections, explanations
```

### 4.1 Data Models (`models.py`)

- **LeaveType** — static leave-type reference with accrual rates, caps
- **Employee** — employee master data relevant to leave calculations
- **LeaveBalance** — running balance with accrued/taken history
- **LeaveTransaction** — single accrual or usage event
- **LeaveExplanation** — human-readable balance report

### 4.2 Holidays Act Rules (`holidays_act.py`)

- Eligibility checks (annual: 12 months, sick/bereavement: 6 months)
- Weekly accrual calculations with pro-rating
- Balance caps (8 weeks annual, 20 days sick)
- Pay method flags (OWP/AWE/RDP)

### 4.3 Accrual Engine (`accrual.py`)

- Parses synthetic leave transactions
- Replays chronologically to compute balances
- Fills missing accrual for new starters (from start date)
- Applies eligibility and cap rules

### 4.4 Balance Calculator (`balance.py`)

- **current_balances_summary()** — DataFrame of all current balances
- **project_balance()** — forward projection with caps
- **project_all_balances()** — all-employee projection DataFrame
- **explain_balances()** — human-readable explanations

## 5. Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| Long-tenure staff with high balances | Capped at 8 weeks annual leave |
| New starters (< 90 days) | No accrual history; computed from start date; vesting check |
| Casual workers | Pro-rated accrual; AWE pay method |
| Part-time workers | Pro-rated accrual; OWP pay method |
| Employees starting mid-window | Accrual starts at their start date (not generation start) |
| Max balance caps | Annual (8w), Sick (20d) enforced during accrual |

## 6. Configuration

Rules are in `configs/leave_rules.yaml`:

```yaml
hours_per_week: 40
hours_per_day: 8

annual_leave:
  weeks_per_year: 4.0
  vesting_months: 12.0
  max_balance_weeks: 8.0

sick_leave:
  days_per_year: 10.0
  vesting_months: 6.0
  max_balance_days: 20.0

bereavement_leave:
  days_per_year: 3.0
  vesting_months: 6.0

ordinary_weekly_pay_method: "average_of_last_4_weeks"
```

## 7. Usage

### CLI

```bash
# Default: current balances + 52-week projection
python scripts/run_leave_engine.py

# As-of a specific date + explanation reports
python scripts/run_leave_engine.py --as-of 2026-06-30 --explain

# Specific employees
python scripts/run_leave_engine.py --employees 1,2,3
```

### Python

```python
from src.leave_engine import LeaveBalanceCalculator

calc = LeaveBalanceCalculator(as_of=dt.date(2026, 6, 30))
summary = calc.current_balances_summary(employees_df, leave_types_df, leave_tx_df)
```

## 8. Outputs

CLI writes to `outputs/leave_balances/`:

| File | Description |
|------|-------------|
| `current_balances.csv` | One row per employee per leave code |
| `balance_projections.csv` | Projected balances N weeks ahead |
| `balance_explanations.txt` | Readable explanations (with `--explain`) |

## 9. Assumptions & Simplifications

- Annual leave accrual is continuous (not tied to anniversary dates)
- Sick/bereavement eligibility simplified to 6 months (actual Act provisions more nuanced)
- Pay calculation methods are simplified flags, not full OWP/AWE calculations
- No parental leave transactions generated (out of scope)
- Rules are configurable and should be reviewed with employment counsel before production use

## 10. Future Enhancements

- Full OWP/AWE pay calculation with actual earnings history
- Leave cash-out / carry-over options
- Anniversary-date-based accrual
- Integration with remuneration costing (leave liability valuation)
- Public holiday + alternative day handling