"""Main entry point for synthetic data generation.

Orchestrates all generators to produce a complete, versioned synthetic
NZ retail workforce dataset. All generators share a single seeded RNG for
full reproducibility.
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from src.common.calendar_utils import build_calendar_frame
from src.common.config import load_synthetic_data_config
from src.common.io import ensure_dir, write_csv, write_manifest
from src.common.validation import validate_all, validate_foreign_keys
from src.synthetic_data.schemas import ALL_SCHEMAS
from src.synthetic_data.generators.stores import generate_stores
from src.synthetic_data.generators.employees import generate_employees
from src.synthetic_data.generators.leave import generate_leave_types, generate_leave_transactions
from src.synthetic_data.generators.rosters import generate_rosters
from src.synthetic_data.generators.demand import generate_demand
from src.synthetic_data.generators.remuneration import generate_remuneration

logger = logging.getLogger(__name__)


def _setup_logging(level: str = "INFO") -> None:
    """Configure the root logger."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def generate_calendar(config: Dict[str, Any]) -> pd.DataFrame:
    """Generate the NZ calendar reference table.

    Parameters
    ----------
    config : Dict[str, Any]
        The full synthetic data config.

    Returns
    -------
    pd.DataFrame
        Calendar table conforming to :data:`CALENDAR_SCHEMA`.
    """
    meta_cfg = config["meta"]
    cal_cfg = config["calendar"]

    start = dt.date.fromisoformat(meta_cfg["start_date"])
    end = dt.date.fromisoformat(meta_cfg["end_date"])

    regions = None
    if cal_cfg.get("include_public_holidays", True):
        regions = cal_cfg.get("regions_with_anniversary_days", [])

    rows = build_calendar_frame(start, end, regions)
    df = pd.DataFrame(rows)
    validate_all(df, ALL_SCHEMAS["calendar_nz"], context="calendar_nz")
    return df


def generate_all(
    config: Optional[Dict[str, Any]] = None,
    *,
    config_path: str = "synthetic_data.yaml",
    output_dir: Optional[str] = None,
    seed: Optional[int] = None,
    log_level: str = "INFO",
) -> Dict[str, pd.DataFrame]:
    """Generate the complete synthetic dataset.

    Parameters
    ----------
    config : Optional[Dict[str, Any]], optional
        Pre-loaded config dict. If ``None``, loaded from ``config_path``.
    config_path : str, optional
        Path to the YAML config (default ``synthetic_data.yaml``).
    output_dir : Optional[str], optional
        Override the output directory from config.
    seed : Optional[int], optional
        Override the random seed from config.
    log_level : str, optional
        Logging level (default ``INFO``).

    Returns
    -------
    Dict[str, pd.DataFrame]
        Mapping of table name → generated DataFrame.
    """
    _setup_logging(log_level)

    if config is None:
        config = load_synthetic_data_config(config_path)

    meta_cfg = config["meta"]
    gen_cfg = config.get("generation", {})

    # Resolve seed
    effective_seed = seed if seed is not None else int(meta_cfg["seed"])
    rng = np.random.default_rng(effective_seed)

    logger.info("Generating synthetic dataset with seed=%d", effective_seed)

    # --- Calendar (needed by other generators) ---
    logger.info("Generating calendar...")
    calendar_df = generate_calendar(config)

    # --- Stores ---
    logger.info("Generating stores...")
    stores_df = generate_stores(rng, config)

    # --- Employees ---
    logger.info("Generating employees...")
    employees_df = generate_employees(rng, config, stores_df)

    # --- Leave types (static) ---
    logger.info("Generating leave types...")
    leave_types_df = generate_leave_types(config)

    # --- Leave transactions ---
    logger.info("Generating leave transactions...")
    leave_transactions_df = generate_leave_transactions(
        rng, config, employees_df, leave_types_df, calendar_df
    )

    # --- Rosters ---
    logger.info("Generating rosters...")
    rosters_df = generate_rosters(rng, config, employees_df, stores_df, calendar_df)

    # --- Demand ---
    logger.info("Generating demand...")
    demand_df = generate_demand(rng, config, stores_df, calendar_df)

    # --- Remuneration ---
    logger.info("Generating remuneration components...")
    remuneration_df = generate_remuneration(rng, config, employees_df)

    tables = {
        "stores": stores_df,
        "employees": employees_df,
        "leave_types": leave_types_df,
        "leave_transactions": leave_transactions_df,
        "rosters": rosters_df,
        "demand": demand_df,
        "remuneration_components": remuneration_df,
        "calendar_nz": calendar_df,
    }

    # --- Cross-table validation ---
    if gen_cfg.get("validate_schemas", True):
        logger.info("Running cross-table validation...")
        validate_foreign_keys(employees_df, "store_id", stores_df, "store_id", context="employees")
        validate_foreign_keys(leave_transactions_df, "employee_id", employees_df, "employee_id", context="leave_transactions")
        validate_foreign_keys(rosters_df, "employee_id", employees_df, "employee_id", context="rosters")
        validate_foreign_keys(rosters_df, "store_id", stores_df, "store_id", context="rosters")
        validate_foreign_keys(demand_df, "store_id", stores_df, "store_id", context="demand")
        validate_foreign_keys(remuneration_df, "employee_id", employees_df, "employee_id", context="remuneration_components")

    # --- Write output ---
    # ``output_dir`` from config already includes the version directory
    # (e.g. ``data/synthetic/v1``). If a ``--output`` override is provided,
    # treat it as the full target directory.
    out_path = ensure_dir(Path(output_dir or meta_cfg["output_dir"]))
    version = meta_cfg.get("version", "v1")

    logger.info("Writing dataset to %s", out_path)
    for name, df in tables.items():
        write_csv(df, out_path / f"{name}.csv")

    # Write manifest
    write_manifest(
        out_path,
        version=version,
        seed=effective_seed,
        tables={name: len(df) for name, df in tables.items()},
        extra={
            "description": meta_cfg.get("description", ""),
            "start_date": meta_cfg.get("start_date"),
            "end_date": meta_cfg.get("end_date"),
            "timezone": meta_cfg.get("timezone"),
        },
    )

    logger.info("Synthetic data generation complete.")
    return tables


def generate_synthetic_data(
    config_path: str = "synthetic_data.yaml",
    output_dir: Optional[str] = None,
    seed: Optional[int] = None,
    log_level: str = "INFO",
) -> Dict[str, pd.DataFrame]:
    """CLI-friendly wrapper around :func:`generate_all`.

    Parameters
    ----------
    config_path : str, optional
        Path to the YAML config (default ``synthetic_data.yaml``).
    output_dir : Optional[str], optional
        Override the output directory from config.
    seed : Optional[int], optional
        Override the random seed from config.
    log_level : str, optional
        Logging level (default ``INFO``).

    Returns
    -------
    Dict[str, pd.DataFrame]
        Mapping of table name → generated DataFrame.
    """
    return generate_all(
        config_path=config_path,
        output_dir=output_dir,
        seed=seed,
        log_level=log_level,
    )