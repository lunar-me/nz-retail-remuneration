#!/usr/bin/env python3
"""CLI entry point for generating the synthetic data layer.

Usage:
    python scripts/generate_synthetic_data.py [--config PATH] [--output DIR] [--seed N] [--log-level LEVEL]

Examples:
    python scripts/generate_synthetic_data.py
    python scripts/generate_synthetic_data.py --seed 123
    python scripts/generate_synthetic_data.py --output data/synthetic/v2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `src` is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    """Run the synthetic data generator from the command line."""
    parser = argparse.ArgumentParser(
        description="Generate the synthetic NZ retail workforce dataset.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="synthetic_data.yaml",
        help="Path to the YAML config file (default: synthetic_data.yaml).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Override the output directory (default: from config).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override the random seed (default: from config).",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO).",
    )
    args = parser.parse_args()

    from src.synthetic_data import generate_synthetic_data

    tables = generate_synthetic_data(
        config_path=args.config,
        output_dir=args.output,
        seed=args.seed,
        log_level=args.log_level,
    )

    print("\n=== Synthetic Data Generation Complete ===")
    print(f"Tables generated: {len(tables)}")
    for name, df in tables.items():
        print(f"  {name:24s} {len(df):>8,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())