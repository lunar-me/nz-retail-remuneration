# Flexible Remuneration Costing & Scenario Model — Design Document

## 1. Purpose

The Flexible Remuneration Costing & Scenario Model provides a transparent,
auditable view of the **true cost of a competitive NZ retail remuneration
package** — base pay + KiwiSaver + leave value + insurance + flexibility
premiums — and lets leadership quantify the cost impact of proposed package
changes before they are promised.

## 2. Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Transparent** | Every cost component is itemised per employee |
| **Auditable** | Formulas are explicit and documented |
| **Scenario-driven** | "What-if" changes are modelled before commitment |
| **Synthetic-data based** | Operates on versioned `data/synthetic/v1` |
| **Linked to leave engine** | Leave balances from Phase 1 inform leave loading value |
| **Extensible** | New components and scenarios add cleanly |

## 3. Cost Model

### 3.1 Fully-Loaded Hourly Cost

For each employee, the fully-loaded hourly cost is:

```
fully_loaded_hourly =
    base_hourly_rate
    + (base_hourly_rate × kiwisaver_employer_rate)          # KiwiSaver
    + (base_hourly_rate × leave_loading_rate)               # Leave value
    + (insurance_monthly_cost / 160)                        # Insurance $/hr
    + (base_hourly_rate × flexibility_premium_rate)         # Flexibility
```

### 3.2 Annual Cost

```
weekly_cost = fully_loaded_hourly × contracted_hours_per_week
annual_cost = weekly_cost × 52
```

### 3.3 Cost Components

| Component | Calculation | Source |
|-----------|-------------|--------|
| Base pay | Contracted hourly rate | `employees.base_hourly_rate` |
| KiwiSaver | 3% × base rate | `remuneration_components` |
| Leave loading | 8% × base rate (illustrative) | `remuneration_components` |
| Insurance | $/month ÷ 160h | `remuneration_components` |
| Flexibility | Up to 6% × base rate | `remuneration_components` |

## 4. Module Architecture

```
src/remuneration/
├── __init__.py
├── models.py       # RemunerationComponents, Scenario, CostAssumptions
├── costing.py      # RemunerationCostingEngine: profiles, summaries, breakdowns
└── scenarios.py    # ScenarioEngine: what-if modelling, comparison reports
```

### 4.1 Data Models (`models.py`)

- **RemunerationComponents** — per-employee cost components with derived
  hourly/weekly/annual costs
- **EmployeeCostProfile** — employee cost breakdown wrapper
- **CostAssumptions** — configurable KiwiSaver, leave loading, insurance,
  flexibility rates
- **Scenario** — a package-change definition with adjustable rates

### 4.2 Costing Engine (`costing.py`)

- **load_components()** — builds components from synthetic tables
- **cost_summary()** — per-employee fully-loaded cost table
- **aggregate_by()** — group by store/role/employment type
- **cost_breakdown()** — annual cost split by component
- **total_annual_cost()** — workforce total

### 4.3 Scenario Engine (`scenarios.py`)

- **run_scenario()** — apply a scenario to all employees, compute impact
- **run_all_scenarios()** — run multiple scenarios
- **scenarios_to_dataframe()** — comparison table
- **default_scenarios()** — built-in illustrative scenarios

## 5. Default Scenarios

| Scenario | Change | Expected Impact |
|----------|--------|-----------------|
| Baseline | Current package | — |
| +2 Days Annual Leave | Leave loading 8% → 10% | ~+2% of leave value |
| +5 Days Sick Leave | Leave loading 8% → 11% | ~+3% of leave value |
| Higher Insurance (+$20/mo) | Insurance +$20/month | ~+$240/employee/year |
| Higher KiwiSaver (4%) | Employer rate 3% → 4% | ~+1% of base pay |
| Flex Premium +2% | Cap 6% → 8% | Scales flexibility premiums |
| Comprehensive Package | All of the above | Combined impact |

## 6. Configuration

Assumptions in `configs/costing_assumptions.yaml`:

```yaml
kiwisaver:
  employer_rate: 0.03

leave_loading:
  base_rate: 0.08
  annual_leave_extra_days_cost: 0.02
  sick_leave_extra_days_cost: 0.03

insurance:
  monthly_employer_cost: {mean: 45, std: 15}
  hours_per_month: 160

flexibility:
  premium_max: 0.06

working_pattern:
  hours_per_week: 40
  weeks_per_year: 52
```

## 7. Usage

### CLI

```bash
# Run all default scenarios
python scripts/run_costing_scenarios.py

# Run specific scenarios
python scripts/run_costing_scenarios.py --scenarios "Baseline,+2 Days Annual Leave"
```

### Python

```python
from src.remuneration import RemunerationCostingEngine, ScenarioEngine

costing = RemunerationCostingEngine()
components = costing.load_components(remuneration_df, employees_df)
summary = costing.cost_summary(remuneration_df, employees_df)

scenario_engine = ScenarioEngine(costing)
comparison = scenario_engine.scenario_comparison(
    scenario_engine.default_scenarios(),
    components,
    costing.total_annual_cost(summary),
)
```

## 8. Outputs

CLI writes to `outputs/costing_scenarios/`:

| File | Description |
|------|-------------|
| `cost_summary.csv` | Per-employee fully-loaded costs |
| `cost_breakdown.csv` | Annual cost by component |
| `scenario_comparison.csv` | Scenario cost impact comparison |

## 9. Assumptions & Simplifications

- KiwiSaver employer contribution simplified to a flat 3%
- Leave loading is an illustrative 8% of base rate (not actual leave liability)
- Insurance cost spread over 160 hours/month
- Flexibility premium scales linearly with preference score
- No penalty rates or shift differentials modelled (rosters handle those)
- Scenario adjustments are simplified rates, not full actuarial models

## 10. Future Enhancements

- Full leave liability valuation using actual leave balances from Phase 1
- Penalty rate and shift differential costing from rosters
- Annual salary vs hourly rate support
- Cost per store with demand-based allocation
- Integration with capacity planner for cost-of-roster analysis