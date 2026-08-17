#!/usr/bin/env python3
"""CLI entry point for the Demand → Roster Capacity Planner.

Usage:
    python scripts/run_capacity_plan.py [--data DIR] [--output DIR]
                                        [--start DATE] [--end DATE]
                                        [--stores ID,ID,...] [--log-level LEVEL]

Examples:
    python scripts/run_capacity_plan.py
    python scripts/run_capacity_plan.py --start 2026-01-01 --end 2026-01-07
    python scripts/run_capacity_plan.py --stores 1,2,3
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
    """Run the capacity planner from the command line."""
    parser = argparse.ArgumentParser(
        description="Run the Demand → Roster Capacity Planner.",
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
        default="outputs/capacity_reports",
        help="Output directory for reports (default: outputs/capacity_reports).",
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2026-06-01",
        help="Start date for capacity analysis (default: 2026-06-01).",
    )
    parser.add_argument(
        "--end",
        type=str,
        default="2026-06-30",
        help="End date for capacity analysis (default: 2026-06-30).",
    )
    parser.add_argument(
        "--stores",
        type=str,
        default=None,
        help="Comma-separated store IDs to analyze (default: all).",
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
    logger = logging.getLogger("capacity")

    from src.capacity import CapacityPlanner, DemandForecaster, RosterSuggester
    from src.capacity.labour_standards import LabourStandards
    from src.common.io import ensure_dir, load_dataset, write_csv

    # Load synthetic data
    logger.info("Loading synthetic data from %s", args.data)
    tables = load_dataset(args.data)
    employees_df = tables["employees"]
    leave_tx_df = tables["leave_transactions"]
    rosters_df = tables["rosters"]
    demand_df = tables["demand"]
    stores_df = tables["stores"]

    # Parse parameters
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    store_ids = None
    if args.stores:
        store_ids = [int(x.strip()) for x in args.stores.split(",")]

    # Filter demand to the date range
    demand_range = demand_df[
        (demand_df["date"] >= start.isoformat())
        & (demand_df["date"] <= end.isoformat())
    ].copy()

    # Build capacity planner
    planner = CapacityPlanner(
        labour_standards=LabourStandards(),
        forecaster=DemandForecaster(),
    )

    # Compute required hours
    logger.info("Computing required labour hours...")
    required = planner.compute_required_hours(demand_range)

    # Compute available hours
    logger.info("Computing available hours (after leave)...")
    available = planner.compute_available_hours(
        employees_df,
        leave_tx_df,
        start,
        end,
        store_ids=store_ids,
        rosters_df=rosters_df,
    )

    # Compute capacity gaps
    logger.info("Computing capacity gaps...")
    gaps = planner.compute_capacity_gaps(required, available)
    gaps_df = planner.gaps_to_dataframe(gaps)

    # Generate roster suggestions
    logger.info("Generating roster suggestions...")
    suggester = RosterSuggester()
    suggestions = suggester.suggest(gaps, available)
    suggestions_df = suggester.suggestions_to_dataframe(suggestions)

    # Summaries
    summary_by_store = planner.summarize_gaps(gaps_df, ["store_id"])
    summary_by_status = gaps_df.groupby("status").agg(
        count=("status", "count"),
        total_gap=("gap_hours", "sum"),
    ).reset_index()

    # Write outputs
    out_dir = ensure_dir(Path(args.output))
    gaps_path = out_dir / "capacity_gaps.csv"
    suggestions_path = out_dir / "roster_suggestions.csv"
    by_store_path = out_dir / "capacity_by_store.csv"
    by_status_path = out_dir / "capacity_by_status.csv"

    write_csv(gaps_df, gaps_path)
    write_csv(suggestions_df, suggestions_path)
    write_csv(summary_by_store, by_store_path)
    write_csv(summary_by_status, by_status_path)

    logger.info("Wrote %s", gaps_path)
    logger.info("Wrote %s", suggestions_path)
    logger.info("Wrote %s", by_store_path)
    logger.info("Wrote %s", by_status_path)

    # Console report
    print("\n=== Capacity Planner Summary ===")
    print(f"Period: {start.isoformat()} to {end.isoformat()}")
    print(f"Stores analyzed: {len(store_ids) if store_ids else len(stores_df)}")
    print(f"Total gap rows: {len(gaps_df)}")
    print(f"Total suggestions: {len(suggestions)}")
    print("\n=== Capacity by Status ===")
    print(summary_by_status.to_string(index=False))
    print("\n=== Top 10 Under-Capacity Gaps ===")
    under = gaps_df[gaps_df["status"] == "UNDER_CAPACITY"].sort_values(
        "gap_hours", ascending=False
    ).head(10)
    if len(under) > 0:
        print(under[["store_id", "date", "role", "gap_hours", "gap_ratio"]].to_string(index=False))
    else:
        print("No under-capacity gaps found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())