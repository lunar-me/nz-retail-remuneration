# Integrated Scorecard & Alerting — Design Document

## 1. Purpose

The Integrated Scorecard combines **total-reward health** and **workforce
availability** into a single view. A manager can see in one place whether
the remuneration package and the roster capacity are both healthy, with
exception alerts flagging problems before they become critical.

## 2. Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Single view** | Programme + store-level metrics in one scorecard |
| **Actionable** | Exception alerts with severity and store attribution |
| **Cross-engine** | Combines outputs from leave, costing, and capacity engines |
| **Threshold-based** | Clear OK / WARNING / CRITICAL status per metric |
| **Synthetic-data driven** | Operates on versioned `data/synthetic/v1` |

## 3. Scorecard Metrics

### 3.1 Programme-Level Metrics

| Metric | Unit | Description | Warning | Critical |
|--------|------|-------------|---------|----------|
| `avg_annual_leave_balance_days` | days | Average annual leave balance (liability proxy) | > 30 | > 50 |
| `insurance_takeup_rate` | pct | % employees enrolled in employer insurance | < 40% | < 30% |
| `avg_flexibility_preference` | score | Average flexibility preference (0–1) | < 0.40 | < 0.30 |
| `total_annual_cost` | $ | Total fully-loaded annual remuneration cost | — | — |
| `avg_fully_loaded_rate` | $/hr | Average fully-loaded cost per hour | — | — |
| `headcount` | employees | Total workforce with composition breakdown | — | — |

### 3.2 Store-Level Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| `headcount` | employees | Store headcount |
| `insurance_takeup` | pct | Store insurance enrolment rate |
| `avg_flexibility` | score | Store average flexibility preference |
| `capacity_ratio` | ratio | Available / required hours over last 7 days |
| `tight_capacity_store` | flag | Store flagged as structurally tight |

## 4. Alerting Rules

| Alert Type | Trigger | Severity |
|------------|---------|----------|
| `leave_liability` | Avg annual balance > 30 days | HIGH |
| `leave_liability` | Avg annual balance > 50 days | CRITICAL |
| `insurance_takeup` | Take-up < 40% | HIGH |
| `insurance_takeup` | Take-up < 30% | CRITICAL |
| `flexibility_utilisation` | Avg flexibility < 0.40 | HIGH |
| `capacity` | Capacity ratio < 0.90 | HIGH |
| `capacity` | Capacity ratio < 0.80 | CRITICAL |
| `tight_capacity` | Store flagged as tight | MEDIUM |

## 5. Module Architecture

```
src/scorecard/
├── __init__.py
├── models.py       # StoreMetric, ProgrammeMetric, Alert, Scorecards
├── metrics.py      # MetricCalculator: programme & store metrics
├── alerts.py       # AlertEngine: exception alert generation
└── scorecard.py    # ScorecardBuilder: combine, render, report
```

### 5.1 Metric Calculator

- **programme_metrics()** — leave liability, insurance take-up, flexibility,
  cost, headcount
- **store_metrics()** — per-store headcount, insurance, flexibility,
  capacity ratio (uses capacity planner)

### 5.2 Alert Engine

- **programme_alerts()** — programme-level exceptions
- **store_alerts()** — store-level exceptions with store attribution

### 5.3 Scorecard Builder

- **build()** — combines all metrics and alerts into `ProgrammeScorecard`
- **render_text()** — readable scorecard report
- **DataFrame converters** — for CSV output

## 6. Usage

### CLI

```bash
# Build scorecard as of 2026-06-30
python scripts/run_scorecard.py

# Different as-of date
python scripts/run_scorecard.py --as-of 2026-06-01
```

### Python

```python
from src.scorecard import ScorecardBuilder

builder = ScorecardBuilder()
scorecard = builder.build(
    employees_df, stores_df, leave_types_df, leave_tx_df,
    remuneration_df, demand_df, rosters_df,
    as_of=dt.date(2026, 6, 30),
)
print(builder.render_text(scorecard))
```

## 7. Outputs

CLI writes to `outputs/scorecards/`:

| File | Description |
|------|-------------|
| `programme_metrics.csv` | Programme-level metrics |
| `store_metrics.csv` | Store-level metrics |
| `alerts.csv` | Exception alerts |
| `scorecard_report.txt` | Readable scorecard report |

## 8. Success Metric

A manager can see in one place:
1. Whether leave liability is under control (avg annual balance < 30 days)
2. Whether the remuneration package is competitive (costs transparent)
3. Whether insurance take-up is healthy (≥ 40%)
4. Whether flexibility is being utilised (avg score ≥ 0.40)
5. Which stores are structurally under-resourced (capacity alerts)

## 9. Assumptions & Simplifications

- Thresholds are configurable defaults
- Capacity metrics use a 7-day lookback window
- Overall health = worst metric status (any warning → WARNING)
- Alerts are rule-based, not ML-based

## 10. Future Enhancements

- Trend tracking (month-over-month metric changes)
- Score weighting for overall health
- Email/notification integration
- Historical alert log
- Custom threshold configuration via YAML