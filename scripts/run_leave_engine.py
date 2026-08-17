#!/usr/bin/env python3
"""CLI entry point for the Leave Entitlement & Accrual Engine.

Usage:
    python scripts/run_leave_engine.py [--data DIR] [--as-of DATE]
                                       [--weeks-ahead N] [--employees ID,ID,...]
                                       [--explain] [--output DIR]

Examples:
    python scripts/run_leave_engine.py
    python scripts/run_leave_engine.py --as-of 2026-06-30
    python scripts/run_leave_engine.py --employees 1,2,3 --explain
    python scripts/run_leave_engine.py --weeks-ahead 26
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    """Run the leave engine from the command line."""
    parser = argparse.ArgumentParser(
        description="Run the NZ Holidays Act-oriented leave engine.",
    )
    parser.add_argument(
        "--data",
        type=str,
        default="data/synthetic/v1",
        help="Path to the synthetic dataset directory (default: data/synthetic/v1).",
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="As-of date for balance calculations (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--weeks-ahead",
        type=float,
        default=52.0,
        help="Weeks to project balances forward (default: 52).",
    )
    parser.add_argument(
        "--employees",
        type=str,
        default=None,
        help="Comma-separated employee IDs to process (default: all).",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Generate balance explanation reports for sample employees.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/leave_balances",
        help="Output directory for reports (default: outputs/leave_balances).",
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
    import datetime as dt

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("leave_engine")

    from src.common.io import ensure_dir, load_dataset, write_csv
    from src.leave_engine import LeaveAccrualEngine, LeaveBalanceCalculator, HolidaysActRules

    # Load synthetic data
    logger.info("Loading synthetic data from %s", args.data)
    tables = load_dataset(args.data)
    employees_df = tables["employees"]
    leave_types_df = tables["leave_types"]
    leave_transactions_df = tables["leave_transactions"]

    # Parse employee filter
    employee_ids = None
    if args.employees:
        employee_ids = [int(x.strip()) for x in args.employees.split(",")]

    # Parse as-of date
    as_of = dt.date.fromisoformat(args.as_of) if args.as_of else dt.date.today()

    # Load leave rules
    from src.common.config import load_yaml
    rules_dict = load_yaml("leave_rules.yaml")
    rules = HolidaysActRules(rules_dict)

    # Create engine & calculator
    engine = LeaveAccrualEngine(rules, as_of=as_of)
    calculator = LeaveBalanceCalculator(engine, as_of=as_of)

    # Compute current balances
    logger.info("Computing current leave balances...")
    summary = calculator.current_balances_summary(
        employees_df,
        leave_types_df,
        leave_transactions_df,
        employee_ids=employee_ids,
    )

    # Compute projections
    logger.info("Projecting balances %s weeks ahead...", args.weeks_ahead)
    projections = calculator.project_all_balances(
        employees_df,
        leave_types_df,
        leave_transactions_df,
        weeks_ahead=args.weeks_ahead,
        employee_ids=employee_ids,
    )

    # Write outputs
    out_dir = ensure_dir(Path(args.output))
    balance_path = out_dir / "current_balances.csv"
    projection_path = out_dir / "balance_projections.csv"

    write_csv(summary, balance_path)
    write_csv(projections, projection_path)
    logger.info("Wrote %s", balance_path)
    logger.info("Wrote %s", projection_path)

    # Print summary to console
    print("\n=== Leave Balance Summary ===")
    print(f"As-of: {as_of.isoformat()}")
    print(f"Employees processed: {summary['employee_id'].nunique()}")
    print(f"Balance rows: {len(summary)}")
    print(f"\nOutput files:")
    print(f"  {balance_path}")
    print(f"  {projection_path}")

    # Optionally generate explanations for sample employees
    if args.explain:
        # Pick a diverse sample: 1 high-leave-balance, 1 new starter, 1 casual
        sample_ids = _select_sample_employees(employees_df, employee_ids)
        logger.info("Generating explanations for sample employees: %s", sample_ids)

        explanations = calculator.explain_balances(
            employees_df,
            leave_types_df,
            leave_transactions_df,
            employee_ids=sample_ids,
        )

        text = calculator.render_explanations_to_text(explanations)
        report_path = out_dir / "balance_explanations.txt"
        report_path.write_text(text, encoding="utf-8")
        print(f"\nExplanations written to: {report_path}")
        print("\n--- Sample ---")
        print(text[:2000])

    return 0


def _select_sample_employees(
    employees_df,
    employee_ids: Optional[List[int]] = None,
) -> list[int]:
    """Select a diverse sample of employees for explanation reports."""
    import pandas as pd

    df = employees_df

    if employee_ids is not None:
        filtered = df[df["employee_id"].isin(employee_ids)]
        return filtered["employee_id"].head(5).tolist()

    # Pick: 1 high-leave-balance, 1 new starter, 1 casual, 2 random
    sample = []

    high_leave = df[df.get("is_high_leave_balance", False) == True]
    if len(high_leave) > 0:
        sample.append(int(high_leave.iloc[0]["employee_id"]))

    new_starters = df[df.get("is_new_starter", False) == True]
    if len(new_starters) > 0:
        sample.append(int(new_starters.iloc[0]["employee_id"]))

    casual = df[df["employment_type"] == "casual"]
    if len(casual) > 0:
        sample.append(int(casual.iloc[0]["employee_id"]))

    # Add a couple of random employees
    rest = df[~df["employee_id"].isin(sample)]
    if len(rest) > 0:
        sample.extend(rest["employee_id"].head(3).tolist())

    return list(dict.fromkeys(sample))[:6]


if __name__ == "__main__":
    raise SystemExit(main())