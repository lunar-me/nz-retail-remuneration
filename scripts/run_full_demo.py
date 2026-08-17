#!/usr/bin/env python3
"""Full-chain demonstration script.

Runs the complete programme pipeline:
  1. Load synthetic data
  2. Leave engine → current balances + explanations
  3. Remuneration costing → cost summary + scenario comparison
  4. Capacity planner → gap analysis + roster suggestions
  5. Scorecard → integrated health view with alerts

Usage:
    python scripts/run_full_demo.py [--data DIR] [--output DIR] [--as-of DATE]
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    """Run the full demonstration."""
    parser = argparse.ArgumentParser(
        description="Run the full NZ Retail Remuneration & Workforce demo.",
    )
    parser.add_argument(
        "--data", type=str, default="data/synthetic/v1",
        help="Synthetic dataset directory (default: data/synthetic/v1).",
    )
    parser.add_argument(
        "--output", type=str, default="outputs/demo",
        help="Output directory (default: outputs/demo).",
    )
    parser.add_argument(
        "--as-of", type=str, default="2026-06-30",
        help="As-of date (default: 2026-06-30).",
    )
    parser.add_argument(
        "--log-level", type=str, default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: WARNING).",
    )
    args = parser.parse_args()

    import logging

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.WARNING),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger = logging.getLogger("demo")

    from src.common.io import ensure_dir, load_dataset
    from src.leave_engine import LeaveBalanceCalculator
    from src.remuneration import RemunerationCostingEngine, ScenarioEngine
    from src.capacity import CapacityPlanner, RosterSuggester
    from src.scorecard import ScorecardBuilder

    print("=" * 70)
    print("NZ RETAIL REMUNERATION & WORKFORCE PROGRAMME - DEMONSTRATION")
    print("=" * 70)

    # 1. Load synthetic data
    print("\n[1/5] Loading synthetic data...")
    tables = load_dataset(args.data)
    print(f"      8 tables loaded from {args.data}")

    # 2. Leave engine
    print("\n[2/5] Leave Entitlement & Accrual Engine...")
    as_of = dt.date.fromisoformat(args.as_of)
    calc = LeaveBalanceCalculator(as_of=as_of)
    leave_summary = calc.current_balances_summary(
        tables["employees"], tables["leave_types"], tables["leave_transactions"]
    )
    annual = leave_summary[leave_summary["leave_code"] == "ANNUAL"]
    print(f"      Balances computed for {leave_summary['employee_id'].nunique()} employees")
    print(f"      Avg annual leave balance: {annual['balance_days'].mean():.1f} days")
    print(f"      Avg sick leave balance: {leave_summary[leave_summary['leave_code']=='SICK']['balance_days'].mean():.1f} days")

    # 3. Remuneration costing
    print("\n[3/5] Flexible Remuneration Costing...")
    costing = RemunerationCostingEngine()
    cost_summary = costing.cost_summary(
        tables["remuneration_components"], tables["employees"]
    )
    total_cost = costing.total_annual_cost(cost_summary)
    breakdown = costing.cost_breakdown(cost_summary)
    print(f"      Total annual cost: ${total_cost:,.0f}")
    print(f"      Avg fully-loaded rate: ${cost_summary['fully_loaded_cost_per_hour'].mean():.2f}/hr")

    # 4. Capacity planner
    print("\n[4/5] Demand -> Capacity Planner...")
    planner = CapacityPlanner()
    start = as_of - dt.timedelta(days=6)
    demand_range = tables["demand"][
        (tables["demand"]["date"] >= start.isoformat())
        & (tables["demand"]["date"] <= as_of.isoformat())
    ]
    required = planner.compute_required_hours(demand_range)
    available = planner.compute_available_hours(
        tables["employees"], tables["leave_transactions"], start, as_of,
        rosters_df=tables["rosters"],
    )
    gaps = planner.compute_capacity_gaps(required, available)
    gaps_df = planner.gaps_to_dataframe(gaps)
    under = int((gaps_df["status"] == "UNDER_CAPACITY").sum())
    over = int((gaps_df["status"] == "OVER_CAPACITY").sum())
    print(f"      Capacity gaps: {len(gaps_df)} ({under} under, {over} over)")

    # 5. Scorecard
    print("\n[5/5] Integrated Scorecard...")
    builder = ScorecardBuilder()
    scorecard = builder.build(
        tables["employees"], tables["stores"], tables["leave_types"],
        tables["leave_transactions"], tables["remuneration_components"],
        tables["demand"], tables["rosters"], as_of=as_of,
    )
    print(f"      Overall health: {scorecard.overall_health}")
    print(f"      Alerts: {len(scorecard.alerts)}")

    # Write demonstration outputs
    out_dir = ensure_dir(Path(args.output))
    leave_path = out_dir / "demo_leave_balances.csv"
    cost_path = out_dir / "demo_cost_summary.csv"
    gap_path = out_dir / "demo_capacity_gaps.csv"
    report_path = out_dir / "demo_scorecard_report.txt"

    from src.common.io import write_csv

    write_csv(leave_summary, leave_path)
    write_csv(cost_summary, cost_path)
    write_csv(gaps_df, gap_path)
    report_text = builder.render_text(scorecard)
    report_path.write_text(report_text, encoding="utf-8")

    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print(f"Outputs written to: {out_dir}")
    print(f"  - {leave_path.name}")
    print(f"  - {cost_path.name}")
    print(f"  - {gap_path.name}")
    print(f"  - {report_path.name}")
    print("=" * 70)

    # Show the scorecard summary
    print(report_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())