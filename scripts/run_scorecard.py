#!/usr/bin/env python3
"""CLI entry point for the Integrated Scorecard & Alerting.

Usage:
    python scripts/run_scorecard.py [--data DIR] [--output DIR] [--as-of DATE] [--log-level LEVEL]

Examples:
    python scripts/run_scorecard.py
    python scripts/run_scorecard.py --as-of 2026-06-30
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
    """Run the integrated scorecard from the command line."""
    parser = argparse.ArgumentParser(
        description="Run the Integrated Scorecard & Alerting.",
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
        default="outputs/scorecards",
        help="Output directory for reports (default: outputs/scorecards).",
    )
    parser.add_argument(
        "--as-of",
        type=str,
        default="2026-06-30",
        help="As-of date for metrics (default: 2026-06-30).",
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
    logger = logging.getLogger("scorecard")

    from src.common.io import ensure_dir, load_dataset, write_csv
    from src.scorecard import ScorecardBuilder

    # Load synthetic data
    logger.info("Loading synthetic data from %s", args.data)
    tables = load_dataset(args.data)

    # Parse as-of date
    as_of = dt.date.fromisoformat(args.as_of)

    # Build scorecard
    logger.info("Building integrated scorecard as of %s...", args.as_of)
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

    # Convert to DataFrames
    prog_df = builder.programme_metrics_to_dataframe(scorecard)
    store_df = builder.store_metrics_to_dataframe(scorecard)
    alerts_df = builder.alerts_to_dataframe(scorecard)

    # Write outputs
    out_dir = ensure_dir(Path(args.output))
    prog_path = out_dir / "programme_metrics.csv"
    store_path = out_dir / "store_metrics.csv"
    alerts_path = out_dir / "alerts.csv"
    report_path = out_dir / "scorecard_report.txt"

    write_csv(prog_df, prog_path)
    write_csv(store_df, store_path)
    write_csv(alerts_df, alerts_path)

    text = builder.render_text(scorecard)
    report_path.write_text(text, encoding="utf-8")

    logger.info("Wrote %s", prog_path)
    logger.info("Wrote %s", store_path)
    logger.info("Wrote %s", alerts_path)
    logger.info("Wrote %s", report_path)

    # Console report
    print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())