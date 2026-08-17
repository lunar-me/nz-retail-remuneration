# Demand → Roster Capacity Planner — Design Document

## 1. Purpose

The Demand → Roster Capacity Planner converts demand signals into required
labour hours, overlays available hours (after leave), and identifies capacity
gaps by store, day, and role. It supports roster managers by flagging
structurally under- or over-resourced stores/periods and suggesting basic
roster adjustments.

## 2. Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Demand-driven** | Required hours derived from demand indices and productivity standards |
| **Leave-aware** | Available hours computed as contracted − leave |
| **Gap-focused** | Clear under/balanced/over status per store-day-role |
| **Role-specific** | Different productivity standards per role family |
| **Flexibility-aware** | Roster suggestions prefer high-flexibility employees |
| **Synthetic-data based** | Operates on versioned `data/synthetic/v1` |

## 3. Core Logic

### 3.1 Labour Requirements

For each store-day, demand is allocated across roles proportionally and
converted to required hours:

```
per_role_demand = demand_index / n_roles
required_hours = per_role_demand / productivity_by_role
```

### 3.2 Productivity Standards

| Role Family | Units per Labour Hour |
|-------------|----------------------|
| Checkout | 28 |
| Fresh | 18 |
| Grocery | 22 |
| Online | 15 |
| Supervisor | 25 |
| Management | 20 |
| Support | 20 |
| Default | 20 |

### 3.3 Available Hours

```
daily_contracted = contracted_hours_per_week / 5
available = daily_contracted − leave_hours_on_day
```

### 3.4 Capacity Gap Status

| Status | Condition |
|--------|-----------|
| UNDER_CAPACITY | available / required < 0.90 |
| BALANCED | 0.90 ≤ ratio ≤ 1.15 |
| OVER_CAPACITY | available / required > 1.15 |

## 4. Module Architecture

```
src/capacity/
├── __init__.py
├── models.py               # LabourRequirement, AvailableHours, CapacityGap, RosterSuggestion
├── labour_standards.py     # LabourStandards: productivity by role
├── demand_forecast.py      # DemandForecaster: profiling, forecasting, peak detection
├── capacity.py             # CapacityPlanner: required hours, available hours, gaps
└── roster_suggestions.py   # RosterSuggester: basic adjustment suggestions
```

### 4.1 Demand Forecaster

- **build_store_profiles()** — avg daily index, day-of-week/month multipliers
- **forecast_day()** — forecast demand for a date
- **forecast_period()** — forecast for a date range
- **identify_peaks()** — flag days above threshold × store average

### 4.2 Capacity Planner

- **compute_required_hours()** — demand → required hours by role
- **compute_available_hours()** — contracted − leave per employee-day
- **compute_capacity_gaps()** — gap analysis with status classification
- **gaps_to_dataframe()** / **summarize_gaps()** — reporting

### 4.3 Roster Suggester

- **suggest()** — generate ADD_SHIFT / REDUCE_HOURS suggestions
- **suggestions_to_dataframe()** — reporting

## 5. Usage

### CLI

```bash
# Default: June 2026 capacity analysis
python scripts/run_capacity_plan.py

# Specific period
python scripts/run_capacity_plan.py --start 2026-01-01 --end 2026-01-07

# Specific stores
python scripts/run_capacity_plan.py --stores 1,2,3
```

### Python

```python
from src.capacity import CapacityPlanner, RosterSuggester

planner = CapacityPlanner()
required = planner.compute_required_hours(demand_df)
available = planner.compute_available_hours(employees_df, leave_tx_df, start, end)
gaps = planner.compute_capacity_gaps(required, available)

suggester = RosterSuggester()
suggestions = suggester.suggest(gaps, available)
```

## 6. Outputs

CLI writes to `outputs/capacity_reports/`:

| File | Description |
|------|-------------|
| `capacity_gaps.csv` | Gap rows per store-day-role |
| `roster_suggestions.csv` | Suggested adjustments |
| `capacity_by_store.csv` | Aggregated gap summary by store |
| `capacity_by_status.csv` | Under/balanced/over counts |

## 7. Edge Cases Handled

- **Tight-capacity stores** — flagged as under-capacity more frequently
- **High-demand periods** (weekends, PHs) — show larger required hours
- **Leave days** — reduce available hours, potentially creating gaps
- **New starters** — not available before their start date
- **No available employees** — suggestion flags "consider hiring/training"

## 8. Assumptions & Simplifications

- Demand allocated equally across roles (real systems use role-specific demand)
- Daily contracted hours = weekly / 5 (ignores weekend patterns)
- Productivity standards are configurable and approximate
- No shift-length optimisation or multi-skill cross-training modelled

## 9. Future Enhancements

- Role-specific demand allocation from department-level demand
- Hourly (not daily) demand granularity
- Cross-training / multi-skill matching
- Optimisation engine for roster suggestions
- Cost-aware capacity planning (link to Phase 2 remuneration)