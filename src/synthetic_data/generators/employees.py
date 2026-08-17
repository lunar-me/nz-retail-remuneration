"""Employee generator.

Creates a realistic NZ retail workforce population with employment types,
roles, contracted hours, tenure, flexibility preferences, and insurance
enrolment. Includes controlled edge cases (high leave balances, new starters,
high-flexibility employees).
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from faker import Faker

from src.synthetic_data.schemas import EMPLOYEES_SCHEMA
from src.common.validation import validate_all


def _weighted_choice(rng: np.random.Generator, items: List[Dict[str, Any]], key: str = "name") -> Any:
    """Pick an item from a weighted list."""
    weights = np.array([item.get("weight", 1.0) for item in items], dtype=float)
    weights = weights / weights.sum()
    idx = rng.choice(len(items), p=weights)
    return items[idx][key]


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a value to [low, high]."""
    return max(low, min(high, value))


def generate_employees(
    rng: np.random.Generator,
    config: Dict[str, Any],
    stores_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate the employees table.

    Parameters
    ----------
    rng : np.random.Generator
        Seeded random number generator.
    config : Dict[str, Any]
        The full synthetic data config.
    stores_df : pd.DataFrame
        The generated stores table (for store_id foreign keys).

    Returns
    -------
    pd.DataFrame
        Employees table conforming to :data:`EMPLOYEES_SCHEMA`.
    """
    emp_cfg = config["employees"]
    meta_cfg = config["meta"]
    edge_cfg = config.get("generation", {}).get("edge_cases", {})

    total_target = int(emp_cfg["total_target"])
    store_ids = stores_df["store_id"].tolist()
    n_stores = len(store_ids)

    # Employment type mix
    type_mix = emp_cfg["employment_type_mix"]
    type_weights = np.array(
        [type_mix["full_time"], type_mix["part_time"], type_mix["casual"]],
        dtype=float,
    )
    type_weights = type_weights / type_weights.sum()
    employment_types = rng.choice(
        ["full_time", "part_time", "casual"],
        size=total_target,
        p=type_weights,
    )

    # Roles
    roles = emp_cfg["roles"]
    role_names = [r["name"] for r in roles]
    role_weights = np.array([r["weight"] for r in roles], dtype=float)
    role_weights = role_weights / role_weights.sum()
    role_choices = rng.choice(role_names, size=total_target, p=role_weights)

    # Job family mapping (simplified: role name → job family)
    job_family_map = {
        "Checkout / Front End": "Checkout",
        "Grocery / Nightfill": "Grocery",
        "Fresh Foods": "Fresh",
        "Online / Click & Collect": "Online",
        "Department Supervisor": "Supervisor",
        "Store Management": "Management",
        "Other / Support": "Support",
    }

    # Contracted hours per employment type
    hours_cfg = emp_cfg["contracted_hours"]
    contracted_hours = np.zeros(total_target, dtype=float)
    for i, etype in enumerate(employment_types):
        h = hours_cfg[etype]
        contracted_hours[i] = _clamp(
            rng.normal(h["mean"], h["std"]),
            h["min"],
            h["max"],
        )

    # Tenure (years)
    tenure_cfg = emp_cfg["tenure_years"]
    tenure_years = np.clip(
        rng.normal(tenure_cfg["mean"], tenure_cfg["std"], size=total_target),
        tenure_cfg["min"],
        tenure_cfg["max"],
    )

    # Start dates: derived from tenure, relative to generation end date
    end_date = dt.date.fromisoformat(meta_cfg["end_date"])
    start_dates = [
        end_date - dt.timedelta(days=int(years * 365.25))
        for years in tenure_years
    ]

    # Base hourly rates by role
    base_rates = np.zeros(total_target, dtype=float)
    for i, role in enumerate(role_choices):
        role_cfg = next(r for r in roles if r["name"] == role)
        lo, hi = role_cfg["typical_hourly_rate_range"]
        base_rates[i] = rng.uniform(lo, hi)

    # Flexibility preference (0–1)
    flex_cfg = emp_cfg["flexibility_preference"]
    flexibility = np.clip(
        rng.normal(flex_cfg["mean"], flex_cfg["std"], size=total_target),
        0.0,
        1.0,
    )

    # Insurance enrolment
    insurance_rate = float(emp_cfg["insurance_enrolment_rate"])
    insurance = rng.random(total_target) < insurance_rate

    # Edge cases
    high_leave_count = int(edge_cfg.get("high_leave_balance_employees", 0))
    new_starter_count = int(edge_cfg.get("new_starters_last_90_days", 0))
    high_flex_count = int(edge_cfg.get("high_flexibility_preference", 0))

    # Assign edge-case flags
    is_high_leave = np.zeros(total_target, dtype=bool)
    is_new_starter = np.zeros(total_target, dtype=bool)
    is_high_flex = np.zeros(total_target, dtype=bool)

    # High leave balance: pick long-tenure employees
    if high_leave_count > 0:
        long_tenure_idx = np.argsort(tenure_years)[-high_leave_count:]
        is_high_leave[long_tenure_idx] = True

    # New starters: pick random employees and set start date within last 90 days
    if new_starter_count > 0:
        new_idx = rng.choice(total_target, size=min(new_starter_count, total_target), replace=False)
        is_new_starter[new_idx] = True
        for i in new_idx:
            days_ago = rng.integers(1, 90)
            start_dates[i] = end_date - dt.timedelta(days=int(days_ago))
            tenure_years[i] = days_ago / 365.25

    # High flexibility: pick employees and boost their flexibility score
    if high_flex_count > 0:
        flex_idx = rng.choice(total_target, size=min(high_flex_count, total_target), replace=False)
        is_high_flex[flex_idx] = True
        flexibility[flex_idx] = rng.uniform(0.85, 1.0, size=len(flex_idx))

    # Assign stores (roughly even distribution, with slight variation)
    store_assignments = rng.integers(0, n_stores, size=total_target)
    assigned_store_ids = [store_ids[i] for i in store_assignments]

    # Generate names
    fake = Faker("en_NZ")
    fake.seed_instance(int(rng.integers(0, 2**31 - 1)))
    first_names = [fake.first_name() for _ in range(total_target)]
    last_names = [fake.last_name() for _ in range(total_target)]

    rows: List[Dict[str, Any]] = []
    for i in range(total_target):
        rows.append(
            {
                "employee_id": i + 1,
                "store_id": assigned_store_ids[i],
                "first_name": first_names[i],
                "last_name": last_names[i],
                "role": role_choices[i],
                "job_family": job_family_map.get(role_choices[i], "Other"),
                "employment_type": employment_types[i],
                "start_date": start_dates[i].isoformat(),
                "contracted_hours_per_week": round(contracted_hours[i], 1),
                "base_hourly_rate": round(base_rates[i], 2),
                "insurance_enrolled": bool(insurance[i]),
                "flexibility_preference": round(flexibility[i], 3),
                "is_high_leave_balance": bool(is_high_leave[i]),
                "is_new_starter": bool(is_new_starter[i]),
                "is_high_flexibility": bool(is_high_flex[i]),
            }
        )

    df = pd.DataFrame(rows)
    validate_all(df, EMPLOYEES_SCHEMA, context="employees")
    return df