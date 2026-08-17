"""Remuneration components generator.

Creates per-employee remuneration component tables (base rate, KiwiSaver,
leave loading, insurance, flexibility premium) and computes fully-loaded
cost-per-hour figures for the costing model.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.synthetic_data.schemas import REMUNERATION_SCHEMA
from src.common.validation import validate_all


def generate_remuneration(
    rng: np.random.Generator,
    config: Dict[str, Any],
    employees_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate the remuneration components table.

    Parameters
    ----------
    rng : np.random.Generator
        Seeded random number generator.
    config : Dict[str, Any]
        The full synthetic data config.
    employees_df : pd.DataFrame
        The generated employees table.

    Returns
    -------
    pd.DataFrame
        Remuneration table conforming to :data:`REMUNERATION_SCHEMA`.
    """
    rem_cfg = config["remuneration"]

    kiwisaver_rate = float(rem_cfg["kiwisaver_rate"])
    leave_loading = float(rem_cfg["leave_loading"])
    insurance_mean = float(rem_cfg["insurance_monthly_employer_cost"]["mean"])
    insurance_std = float(rem_cfg["insurance_monthly_employer_cost"]["std"])
    flex_premium_max = float(rem_cfg["flexibility_premium_max"])

    rows: List[Dict[str, Any]] = []

    for _, emp in employees_df.iterrows():
        emp_id = int(emp["employee_id"])
        base_rate = float(emp["base_hourly_rate"])
        insurance_enrolled = bool(emp["insurance_enrolled"])
        flexibility = float(emp["flexibility_preference"])
        contracted_hours = float(emp["contracted_hours_per_week"])

        # KiwiSaver employer contribution (per hour)
        kiwisaver_cost_per_hour = base_rate * kiwisaver_rate

        # Leave loading (value of leave in package, per hour)
        leave_loading_cost_per_hour = base_rate * leave_loading

        # Insurance: monthly cost → per-hour cost (assume ~160 hours/month)
        if insurance_enrolled:
            insurance_monthly = max(0.0, rng.normal(insurance_mean, insurance_std))
        else:
            insurance_monthly = 0.0
        insurance_cost_per_hour = insurance_monthly / 160.0

        # Flexibility premium: scales with flexibility preference
        flex_rate = flexibility * flex_premium_max
        flex_cost_per_hour = base_rate * flex_rate

        # Fully-loaded cost per hour
        fully_loaded = (
            base_rate
            + kiwisaver_cost_per_hour
            + leave_loading_cost_per_hour
            + insurance_cost_per_hour
            + flex_cost_per_hour
        )

        rows.append(
            {
                "employee_id": emp_id,
                "base_hourly_rate": round(base_rate, 2),
                "kiwisaver_employer_rate": kiwisaver_rate,
                "kiwisaver_employer_cost_per_hour": round(kiwisaver_cost_per_hour, 2),
                "leave_loading_rate": leave_loading,
                "leave_loading_cost_per_hour": round(leave_loading_cost_per_hour, 2),
                "insurance_monthly_cost": round(insurance_monthly, 2),
                "insurance_cost_per_hour": round(insurance_cost_per_hour, 2),
                "flexibility_premium_rate": round(flex_rate, 4),
                "flexibility_premium_cost_per_hour": round(flex_cost_per_hour, 2),
                "fully_loaded_cost_per_hour": round(fully_loaded, 2),
            }
        )

    df = pd.DataFrame(rows)
    validate_all(df, REMUNERATION_SCHEMA, context="remuneration_components")
    return df