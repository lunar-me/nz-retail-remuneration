"""Leave types and leave transaction generator.

Creates the static leave-types reference table and realistic leave accrual
and usage transactions with NZ Holidays Act-oriented patterns (winter sick
leave peaks, annual leave around Christmas/school holidays, etc.).
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.synthetic_data.schemas import LEAVE_TYPES_SCHEMA, LEAVE_TRANSACTIONS_SCHEMA
from src.common.validation import validate_all


def generate_leave_types(config: Dict[str, Any]) -> pd.DataFrame:
    """Generate the static leave-types reference table.

    Parameters
    ----------
    config : Dict[str, Any]
        The ``leave`` section of the synthetic data config.

    Returns
    -------
    pd.DataFrame
        Leave types table conforming to :data:`LEAVE_TYPES_SCHEMA`.
    """
    leave_cfg = config["leave"]
    rows: List[Dict[str, Any]] = []

    for lt in leave_cfg["types"]:
        rows.append(
            {
                "leave_code": lt["code"],
                "leave_name": lt["name"],
                "is_paid": lt.get("is_paid", True),
                "carries_over": lt.get("carries_over", False),
                "accrual_rate_hours_per_week": lt.get("accrual_rate_hours_per_week"),
                "accrual_rate_days_per_year": lt.get("accrual_rate_days_per_year"),
                "max_balance_weeks": lt.get("max_balance_weeks"),
                "max_balance_days": lt.get("max_balance_days"),
            }
        )

    df = pd.DataFrame(rows)
    validate_all(df, LEAVE_TYPES_SCHEMA, context="leave_types")
    return df


def _annual_leave_usage_probability(month: int) -> float:
    """Return the probability of taking annual leave in a given month.

    Peaks around Christmas/New Year (Dec–Jan) and school holidays (April).
    """
    peak_months = {12: 0.30, 1: 0.25, 4: 0.15}
    return peak_months.get(month, 0.05)


def _sick_leave_usage_probability(month: int, winter_multiplier: float) -> float:
    """Return the probability of taking sick leave in a given month.

    Higher in winter (May–September).
    """
    base = 0.03
    if month in (5, 6, 7, 8, 9):
        return base * winter_multiplier
    return base


def generate_leave_transactions(
    rng: np.random.Generator,
    config: Dict[str, Any],
    employees_df: pd.DataFrame,
    leave_types_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate leave accrual and usage transactions.

    Parameters
    ----------
    rng : np.random.Generator
        Seeded random number generator.
    config : Dict[str, Any]
        The full synthetic data config.
    employees_df : pd.DataFrame
        The generated employees table.
    leave_types_df : pd.DataFrame
        The generated leave-types reference table.
    calendar_df : pd.DataFrame
        The generated calendar table.

    Returns
    -------
    pd.DataFrame
        Leave transactions table conforming to :data:`LEAVE_TRANSACTIONS_SCHEMA`.
    """
    leave_cfg = config["leave"]
    usage_cfg = leave_cfg["usage_patterns"]
    meta_cfg = config["meta"]

    start_date = dt.date.fromisoformat(meta_cfg["start_date"])
    end_date = dt.date.fromisoformat(meta_cfg["end_date"])

    # Build lookup maps
    leave_type_map = {
        row["leave_code"]: row.to_dict()
        for _, row in leave_types_df.iterrows()
    }

    # Calendar lookup: date → row
    calendar_map = {
        row["date"]: row.to_dict()
        for _, row in calendar_df.iterrows()
    }

    # Employee lookup
    employee_map = {
        row["employee_id"]: row.to_dict()
        for _, row in employees_df.iterrows()
    }

    transactions: List[Dict[str, Any]] = []
    tx_id = 1

    # Weekly accrual for annual leave (hours per week)
    annual_accrual_rate = leave_type_map["ANNUAL"].get("accrual_rate_hours_per_week", 3.0769)
    sick_accrual_days = leave_type_map["SICK"].get("accrual_rate_days_per_year", 10)

    for emp_id, emp in employee_map.items():
        emp_start = dt.date.fromisoformat(emp["start_date"])
        contracted_hours = float(emp["contracted_hours_per_week"])
        employment_type = emp["employment_type"]
        is_high_leave = emp["is_high_leave_balance"]

        # Annual leave balance tracking
        annual_balance = 0.0
        sick_balance = 0.0

        # Iterate week by week from employee start (or generation start)
        current = max(emp_start, start_date)
        # Align to Monday
        current = current - dt.timedelta(days=current.weekday())

        while current <= end_date:
            # --- Annual leave accrual (weekly) ---
            # Pro-rata for part-time/casual based on contracted hours
            accrual_factor = contracted_hours / 40.0
            weekly_accrual = annual_accrual_rate * accrual_factor
            annual_balance += weekly_accrual

            # Cap at max balance (weeks * 40 hours)
            max_weeks = leave_type_map["ANNUAL"].get("max_balance_weeks", 8)
            annual_balance = min(annual_balance, max_weeks * 40.0)

            # --- Sick leave accrual (annual, pro-rated) ---
            sick_weekly = (sick_accrual_days * 8.0) / 52.0 * accrual_factor
            sick_balance += sick_weekly
            max_sick_days = leave_type_map["SICK"].get("max_balance_days", 20)
            sick_balance = min(sick_balance, max_sick_days * 8.0)

            # Record weekly accrual transaction
            transactions.append(
                {
                    "transaction_id": tx_id,
                    "employee_id": emp_id,
                    "leave_code": "ANNUAL",
                    "transaction_date": current.isoformat(),
                    "transaction_type": "ACCRUAL",
                    "hours": round(weekly_accrual, 2),
                    "balance_after": round(annual_balance, 2),
                    "reason_code": None,
                }
            )
            tx_id += 1

            transactions.append(
                {
                    "transaction_id": tx_id,
                    "employee_id": emp_id,
                    "leave_code": "SICK",
                    "transaction_date": current.isoformat(),
                    "transaction_type": "ACCRUAL",
                    "hours": round(sick_weekly, 2),
                    "balance_after": round(sick_balance, 2),
                    "reason_code": None,
                }
            )
            tx_id += 1

            # --- Annual leave usage ---
            # Check each day in the week for potential annual leave
            for day_offset in range(7):
                day = current + dt.timedelta(days=day_offset)
                if day > end_date:
                    break

                month = day.month
                prob = _annual_leave_usage_probability(month)

                # High-leave-balance employees take more leave
                if is_high_leave:
                    prob *= 1.3

                if rng.random() < prob and annual_balance >= 8.0:
                    # Take a day (8 hours) of annual leave
                    hours_taken = 8.0
                    annual_balance -= hours_taken
                    transactions.append(
                        {
                            "transaction_id": tx_id,
                            "employee_id": emp_id,
                            "leave_code": "ANNUAL",
                            "transaction_date": day.isoformat(),
                            "transaction_type": "TAKEN",
                            "hours": round(hours_taken, 2),
                            "balance_after": round(annual_balance, 2),
                            "reason_code": "ANNUAL_LEAVE",
                        }
                    )
                    tx_id += 1

                # --- Sick leave usage ---
                sick_prob = _sick_leave_usage_probability(month, usage_cfg["sick"]["winter_multiplier"])
                if rng.random() < sick_prob and sick_balance >= 8.0:
                    hours_taken = 8.0
                    sick_balance -= hours_taken
                    transactions.append(
                        {
                            "transaction_id": tx_id,
                            "employee_id": emp_id,
                            "leave_code": "SICK",
                            "transaction_date": day.isoformat(),
                            "transaction_type": "TAKEN",
                            "hours": round(hours_taken, 2),
                            "balance_after": round(sick_balance, 2),
                            "reason_code": "SICK_LEAVE",
                        }
                    )
                    tx_id += 1

            current += dt.timedelta(days=7)

        # --- Bereavement leave (rare, annual probability) ---
        bereavement_prob = usage_cfg["bereavement"]["annual_probability"]
        if rng.random() < bereavement_prob:
            # Take 1–3 days
            days_taken = rng.integers(1, 4)
            # Pick a random date in the window
            random_day = start_date + dt.timedelta(
                days=int(rng.integers(0, (end_date - start_date).days))
            )
            transactions.append(
                {
                    "transaction_id": tx_id,
                    "employee_id": emp_id,
                    "leave_code": "BEREAVEMENT",
                    "transaction_date": random_day.isoformat(),
                    "transaction_type": "TAKEN",
                    "hours": round(float(days_taken) * 8.0, 2),
                    "balance_after": 0.0,
                    "reason_code": "BEREAVEMENT",
                }
            )
            tx_id += 1

    df = pd.DataFrame(transactions)
    validate_all(df, LEAVE_TRANSACTIONS_SCHEMA, context="leave_transactions")
    return df