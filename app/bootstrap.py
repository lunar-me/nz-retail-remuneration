"""Bootstrap: generate pre-computed outputs if they are missing.

On Streamlit Cloud only git-tracked files are deployed. The ``outputs/``
directory is git-ignored, so it does not exist on the deployed instance.
This module regenerates all outputs the app needs from the committed
synthetic dataset (``data/synthetic/v1``) the first time the app starts.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DATA_DIR = PROJECT_ROOT / "data" / "synthetic" / "v1"

# Files the app reads (see app/utils.py)
REQUIRED_FILES = {
    "leave_balances": [
        "current_balances.csv",
        "balance_projections.csv",
        "balance_explanations.txt",
    ],
    "costing_scenarios": [
        "cost_summary.csv",
        "cost_breakdown.csv",
        "scenario_comparison.csv",
    ],
    "capacity_reports": [
        "capacity_gaps.csv",
        "roster_suggestions.csv",
        "capacity_by_store.csv",
        "capacity_by_status.csv",
    ],
    "scorecards": [
        "programme_metrics.csv",
        "store_metrics.csv",
        "alerts.csv",
        "scorecard_report.txt",
    ],
}


def _outputs_missing() -> bool:
    """Return True if any required output file is absent."""
    for subdir, files in REQUIRED_FILES.items():
        for f in files:
            if not (OUTPUTS_DIR / subdir / f).exists():
                return True
    return False


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to CSV, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _select_sample_employees(employees_df: pd.DataFrame) -> list[int]:
    """Select a diverse sample of employees for explanation reports."""
    sample: list[int] = []

    high = employees_df[employees_df.get("is_high_leave_balance", False) == True]  # noqa: E712
    if len(high) > 0:
        sample.append(int(high.iloc[0]["employee_id"]))

    new = employees_df[employees_df.get("is_new_starter", False) == True]  # noqa: E712
    if len(new) > 0:
        sample.append(int(new.iloc[0]["employee_id"]))

    casual = employees_df[employees_df["employment_type"] == "casual"]
    if len(casual) > 0:
        sample.append(int(casual.iloc[0]["employee_id"]))

    rest = employees_df[~employees_df["employee_id"].isin(sample)]
    if len(rest) > 0:
        sample.extend(rest["employee_id"].head(3).tolist())

    return list(dict.fromkeys(sample))[:6]


def _generate_leave_balances(tables: dict) -> None:
    """Generate leave_balances outputs."""
    from src.common.config import load_yaml
    from src.leave_engine import HolidaysActRules, LeaveAccrualEngine, LeaveBalanceCalculator

    as_of = dt.date(2026, 6, 30)
    rules = HolidaysActRules(load_yaml("leave_rules.yaml"))
    engine = LeaveAccrualEngine(rules, as_of=as_of)
    calculator = LeaveBalanceCalculator(engine, as_of=as_of)

    employees_df = tables["employees"]
    leave_types_df = tables["leave_types"]
    leave_tx_df = tables["leave_transactions"]

    summary = calculator.current_balances_summary(employees_df, leave_types_df, leave_tx_df)
    projections = calculator.project_all_balances(
        employees_df, leave_types_df, leave_tx_df, weeks_ahead=52.0
    )

    out = OUTPUTS_DIR / "leave_balances"
    _write_csv(summary, out / "current_balances.csv")
    _write_csv(projections, out / "balance_projections.csv")

    sample_ids = _select_sample_employees(employees_df)
    explanations = calculator.explain_balances(
        employees_df, leave_types_df, leave_tx_df, employee_ids=sample_ids
    )
    text = calculator.render_explanations_to_text(explanations)
    (out / "balance_explanations.txt").write_text(text, encoding="utf-8")


def _generate_costing(tables: dict) -> None:
    """Generate costing_scenarios outputs."""
    from src.remuneration import RemunerationCostingEngine, ScenarioEngine

    employees_df = tables["employees"]
    remuneration_df = tables["remuneration_components"]

    costing = RemunerationCostingEngine()
    components = costing.load_components(remuneration_df, employees_df)
    summary = costing.cost_summary(remuneration_df, employees_df)
    base_annual_cost = costing.total_annual_cost(summary)
    breakdown = costing.cost_breakdown(summary)

    scenario_engine = ScenarioEngine(costing)
    scenarios = scenario_engine.default_scenarios()
    results = scenario_engine.run_all_scenarios(scenarios, components, base_annual_cost)
    comparison = scenario_engine.scenarios_to_dataframe(results)

    breakdown_df = pd.DataFrame(
        [{"component": k, "annual_cost": round(v, 2)} for k, v in breakdown.items()]
    )

    out = OUTPUTS_DIR / "costing_scenarios"
    _write_csv(summary, out / "cost_summary.csv")
    _write_csv(breakdown_df, out / "cost_breakdown.csv")
    _write_csv(comparison, out / "scenario_comparison.csv")


def _generate_capacity(tables: dict) -> None:
    """Generate capacity_reports outputs."""
    from src.capacity import CapacityPlanner, DemandForecaster, LabourStandards, RosterSuggester

    employees_df = tables["employees"]
    leave_tx_df = tables["leave_transactions"]
    rosters_df = tables["rosters"]
    demand_df = tables["demand"]

    start = dt.date(2026, 6, 1)
    end = dt.date(2026, 6, 30)

    demand_range = demand_df[
        (demand_df["date"] >= start.isoformat()) & (demand_df["date"] <= end.isoformat())
    ].copy()

    planner = CapacityPlanner(
        labour_standards=LabourStandards(),
        forecaster=DemandForecaster(),
    )
    required = planner.compute_required_hours(demand_range)
    available = planner.compute_available_hours(
        employees_df, leave_tx_df, start, end, rosters_df=rosters_df
    )
    gaps = planner.compute_capacity_gaps(required, available)
    gaps_df = planner.gaps_to_dataframe(gaps)

    suggester = RosterSuggester()
    suggestions = suggester.suggest(gaps, available)
    suggestions_df = suggester.suggestions_to_dataframe(suggestions)

    summary_by_store = planner.summarize_gaps(gaps_df, ["store_id"])
    summary_by_status = (
        gaps_df.groupby("status")
        .agg(count=("status", "count"), total_gap=("gap_hours", "sum"))
        .reset_index()
    )

    out = OUTPUTS_DIR / "capacity_reports"
    _write_csv(gaps_df, out / "capacity_gaps.csv")
    _write_csv(suggestions_df, out / "roster_suggestions.csv")
    _write_csv(summary_by_store, out / "capacity_by_store.csv")
    _write_csv(summary_by_status, out / "capacity_by_status.csv")


def _generate_scorecard(tables: dict) -> None:
    """Generate scorecards outputs."""
    from src.scorecard import ScorecardBuilder

    as_of = dt.date(2026, 6, 30)
    builder = ScorecardBuilder()
    scorecard = builder.build(
        tables["employees"],
        tables["stores"],
        tables["leave_types"],
        tables["leave_transactions"],
        tables["remuneration_components"],
        tables["demand"],
        tables["rosters"],
        as_of=as_of,
    )

    prog_df = builder.programme_metrics_to_dataframe(scorecard)
    store_df = builder.store_metrics_to_dataframe(scorecard)
    alerts_df = builder.alerts_to_dataframe(scorecard)
    text = builder.render_text(scorecard)

    out = OUTPUTS_DIR / "scorecards"
    _write_csv(prog_df, out / "programme_metrics.csv")
    _write_csv(store_df, out / "store_metrics.csv")
    _write_csv(alerts_df, out / "alerts.csv")
    (out / "scorecard_report.txt").write_text(text, encoding="utf-8")


def ensure_outputs() -> None:
    """Generate all pre-computed outputs if any are missing."""
    if not _outputs_missing():
        return

    from src.common.io import load_dataset

    tables = load_dataset(DATA_DIR)

    _generate_leave_balances(tables)
    _generate_costing(tables)
    _generate_capacity(tables)
    _generate_scorecard(tables)