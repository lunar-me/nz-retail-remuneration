#!/usr/bin/env python3
"""CLI entry point for the Remuneration Costing & Scenario Model.

Usage:
    python scripts/run_costing_scenarios.py [--data DIR] [--output DIR]
                                            [--scenarios NAME,NAME,...] [--log-level LEVEL]

Examples:
    python scripts/run_costing_scenarios.py
    python scripts/run_costing_scenarios.py --scenarios "Baseline,+2 Days Annual Leave"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    """Run the remuneration costing engine from the command line."""
    parser = argparse.ArgumentParser(
        description="Run the Flexible Remuneration Costing & Scenario Model.",
    )
    parser.add_argument(
        "--data",
        type=str,
        default="data/synthetic/v1",
        help="Path to the synthetic dataset directory (default: data/synthetic/v1).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/costing_scenarios",
        help="Output directory for reports (default: outputs/costing_scenarios).",
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        default=None,
        help="Comma-separated scenario names to run (default: all built-in).",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO).",
    )
    args = parser.parse_args()

    import logging

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("remuneration")

    from src.common.io import ensure_dir, load_dataset, write_csv
    from src.remuneration import RemunerationCostingEngine, ScenarioEngine
    from src.remuneration.scenarios import Scenario

    # Load synthetic data
    logger.info("Loading synthetic data from %s", args.data)
    tables = load_dataset(args.data)
    employees_df = tables["employees"]
    remuneration_df = tables["remuneration_components"]

    # Build costing engine & load components
    logger.info("Building remuneration cost profiles...")
    costing = RemunerationCostingEngine()
    components = costing.load_components(remuneration_df, employees_df)

    # Compute baseline cost summary
    summary = costing.cost_summary(remuneration_df, employees_df)
    base_annual_cost = costing.total_annual_cost(summary)
    breakdown = costing.cost_breakdown(summary)

    # Determine scenarios to run
    scenario_engine = ScenarioEngine(costing)
    all_scenarios = scenario_engine.default_scenarios()

    if args.scenarios:
        requested = {name.strip() for name in args.scenarios.split(",")}
        scenarios = [s for s in all_scenarios if s.name in requested]
    else:
        scenarios = all_scenarios

    logger.info("Running %d scenarios...", len(scenarios))
    results = scenario_engine.run_all_scenarios(scenarios, components, base_annual_cost)
    comparison = scenario_engine.scenarios_to_dataframe(results)

    # Write outputs
    out_dir = ensure_dir(Path(args.output))
    summary_path = out_dir / "cost_summary.csv"
    breakdown_path = out_dir / "cost_breakdown.csv"
    comparison_path = out_dir / "scenario_comparison.csv"

    write_csv(summary, summary_path)
    breakdown_df = _breakdown_to_df(breakdown)
    write_csv(breakdown_df, breakdown_path)
    write_csv(comparison, comparison_path)

    logger.info("Wrote %s", summary_path)
    logger.info("Wrote %s", breakdown_path)
    logger.info("Wrote %s", comparison_path)

    # Console report
    print("\n=== Remuneration Costing Summary ===")
    print(f"Employees: {len(summary)}")
    print(f"Base total annual cost: ${base_annual_cost:,.0f}")
    print(f"Avg fully-loaded rate: ${summary['fully_loaded_cost_per_hour'].mean():.2f}/hr")
    print("\nCost Breakdown (annual):")
    for component, amount in breakdown.items():
        if component == "total":
            continue
        pct = (amount / breakdown["total"] * 100) if breakdown["total"] else 0
        print(f"  {component:15s} ${amount:>12,.0f}  ({pct:.1f}%)")
    print(f"  {'TOTAL':15s} ${breakdown['total']:>12,.0f}")

    print("\n=== Scenario Comparison ===")
    print(comparison.to_string(index=False))

    # Print aggregation by employment type
    by_type = costing.aggregate_by(summary, ["employment_type"])
    print("\n=== Cost by Employment Type ===")
    print(by_type.to_string(index=False))

    return 0


def _breakdown_to_df(breakdown: dict):
    """Convert a cost breakdown dict to a DataFrame."""
    import pandas as pd

    rows = [{"component": k, "annual_cost": round(v, 2)} for k, v in breakdown.items()]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    raise SystemExit(main())