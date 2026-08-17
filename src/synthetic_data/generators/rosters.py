"""Roster / worked-hours generator.

Creates realistic shift patterns for employees across the generation window,
respecting contracted hours, employment type, weekend work probabilities,
public-holiday work, and NZ retail trading patterns.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.synthetic_data.schemas import ROSTERS_SCHEMA
from src.common.validation import validate_all


def _parse_time(time_str: str) -> dt.time:
    """Parse an HH:MM time string into a time object."""
    return dt.time.fromisoformat(time_str)


def _to_date(value: Any) -> dt.date:
    """Convert a date-like value to a datetime.date object."""
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        return dt.date.fromisoformat(value)
    if isinstance(value, dt.datetime):
        return value.date()
    raise ValueError(f"Cannot convert {type(value)} to date")


def _shift_hours(start: dt.time, end: dt.time) -> float:
    """Compute shift duration in hours (handles overnight shifts)."""
    start_min = start.hour * 60 + start.minute
    end_min = end.hour * 60 + end.minute
    if end_min <= start_min:
        end_min += 24 * 60
    return (end_min - start_min) / 60.0


def generate_rosters(
    rng: np.random.Generator,
    config: Dict[str, Any],
    employees_df: pd.DataFrame,
    stores_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate the roster / worked-hours table.

    Parameters
    ----------
    rng : np.random.Generator
        Seeded random number generator.
    config : Dict[str, Any]
        The full synthetic data config.
    employees_df : pd.DataFrame
        The generated employees table.
    stores_df : pd.DataFrame
        The generated stores table.
    calendar_df : pd.DataFrame
        The generated calendar table.

    Returns
    -------
    pd.DataFrame
        Rosters table conforming to :data:`ROSTERS_SCHEMA`.
    """
    roster_cfg = config["rosters"]
    meta_cfg = config["meta"]

    start_date = dt.date.fromisoformat(meta_cfg["start_date"])
    end_date = dt.date.fromisoformat(meta_cfg["end_date"])

    # Store lookup: store_id → trading hours
    store_map = {
        row["store_id"]: row.to_dict()
        for _, row in stores_df.iterrows()
    }

    # Calendar lookup: date → row (normalise to date objects)
    calendar_map = {
        _to_date(row["date"]): row.to_dict()
        for _, row in calendar_df.iterrows()
    }

    # Employee lookup
    employee_map = {
        row["employee_id"]: row.to_dict()
        for _, row in employees_df.iterrows()
    }

    # Shift length options
    shift_lengths = [int(x) for x in roster_cfg["typical_shift_lengths"]]

    # Utilisation by employment type
    utilisation = roster_cfg["utilisation"]

    # Weekend work probability by employment type
    weekend_prob = roster_cfg["weekend_work_probability"]

    # Public holiday work probability
    ph_prob = float(roster_cfg["public_holiday_work_probability"])

    rows: List[Dict[str, Any]] = []
    roster_id = 1

    for emp_id, emp in employee_map.items():
        store_id = int(emp["store_id"])
        store = store_map[store_id]
        employment_type = emp["employment_type"]
        contracted_hours = float(emp["contracted_hours_per_week"])
        role = emp["role"]
        emp_start = dt.date.fromisoformat(emp["start_date"])

        # Weekly target hours based on utilisation
        weekly_target = contracted_hours * utilisation[employment_type]

        # Iterate week by week
        current = max(emp_start, start_date)
        current = current - dt.timedelta(days=current.weekday())  # align to Monday

        while current <= end_date:
            # Determine which days this employee works this week
            # Base: work ~5 days for full-time, fewer for part-time/casual
            if employment_type == "full_time":
                n_days = 5
            elif employment_type == "part_time":
                n_days = rng.integers(3, 6)
            else:  # casual
                n_days = rng.integers(1, 5)

            # Choose days (weighted toward weekends for part-time/casual)
            days = list(range(7))
            weights = np.ones(7)
            if employment_type in ("part_time", "casual"):
                weights[5] *= 1.5  # Saturday
                weights[6] *= 1.3  # Sunday

            chosen_days = rng.choice(days, size=n_days, replace=False, p=weights / weights.sum())

            for day_idx in chosen_days:
                day = current + dt.timedelta(days=int(day_idx))
                if day > end_date:
                    continue

                cal = calendar_map[day]
                is_weekend = bool(cal["is_weekend"])
                is_ph = bool(cal["is_public_holiday"])

                # Skip if public holiday and employee not selected to work
                if is_ph and rng.random() > ph_prob:
                    continue

                # Skip weekend if employee not selected for weekend work
                if is_weekend and rng.random() > weekend_prob[employment_type]:
                    continue

                # Choose shift length
                shift_len = rng.choice(shift_lengths)

                # Determine shift start time based on store trading hours
                if is_weekend:
                    if day.weekday() == 5:  # Saturday
                        open_t = _parse_time(store["saturday_open"])
                        close_t = _parse_time(store["saturday_close"])
                    else:  # Sunday
                        open_t = _parse_time(store["sunday_open"])
                        close_t = _parse_time(store["sunday_close"])
                else:
                    open_t = _parse_time(store["weekday_open"])
                    close_t = _parse_time(store["weekday_close"])

                # Random start within trading hours (leaving room for shift length)
                open_min = open_t.hour * 60 + open_t.minute
                close_min = close_t.hour * 60 + close_t.minute
                max_start = max(open_min, close_min - shift_len * 60)
                start_min = rng.integers(open_min, max_start + 1)
                end_min = start_min + shift_len * 60

                start_time = dt.time(start_min // 60, start_min % 60)
                end_time = dt.time(end_min // 60, end_min % 60)

                # Penalty flag: weekend or public holiday work
                penalty = is_weekend or is_ph

                rows.append(
                    {
                        "roster_id": roster_id,
                        "employee_id": emp_id,
                        "store_id": store_id,
                        "work_date": day.isoformat(),
                        "shift_start": start_time.isoformat(),
                        "shift_end": end_time.isoformat(),
                        "hours_worked": round(float(shift_len), 1),
                        "role_on_day": role,
                        "is_weekend": is_weekend,
                        "is_public_holiday": is_ph,
                        "penalty_flag": penalty,
                    }
                )
                roster_id += 1

            current += dt.timedelta(days=7)

    df = pd.DataFrame(rows)
    validate_all(df, ROSTERS_SCHEMA, context="rosters")
    return df