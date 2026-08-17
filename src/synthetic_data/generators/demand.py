"""Demand / activity driver generator.

Creates daily demand indices, transaction counts, and sales amounts per store,
incorporating NZ retail seasonality (weekend peaks, public-holiday spikes,
Christmas, school holidays) and controlled noise.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.synthetic_data.schemas import DEMAND_SCHEMA
from src.common.validation import validate_all


def _to_date(value: Any) -> dt.date:
    """Convert a date-like value to a datetime.date object."""
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        return dt.date.fromisoformat(value)
    if isinstance(value, dt.datetime):
        return value.date()
    raise ValueError(f"Cannot convert {type(value)} to date")


def generate_demand(
    rng: np.random.Generator,
    config: Dict[str, Any],
    stores_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate the demand / activity table.

    Parameters
    ----------
    rng : np.random.Generator
        Seeded random number generator.
    config : Dict[str, Any]
        The full synthetic data config.
    stores_df : pd.DataFrame
        The generated stores table.
    calendar_df : pd.DataFrame
        The generated calendar table.

    Returns
    -------
    pd.DataFrame
        Demand table conforming to :data:`DEMAND_SCHEMA`.
    """
    demand_cfg = config["demand"]
    meta_cfg = config["meta"]

    start_date = dt.date.fromisoformat(meta_cfg["start_date"])
    end_date = dt.date.fromisoformat(meta_cfg["end_date"])

    # Calendar lookup: date → row (normalise to date objects)
    calendar_map = {
        _to_date(row["date"]): row.to_dict()
        for _, row in calendar_df.iterrows()
    }

    # Store size factor: larger stores have higher base demand
    size_factor = {
        "Small": 0.6,
        "Medium": 1.0,
        "Large": 1.4,
        "Extra Large": 1.8,
    }

    # Day-of-week multipliers
    dow_mult = {int(k): float(v) for k, v in demand_cfg["day_of_week_multipliers"].items()}

    # Month multipliers
    month_mult = {int(k): float(v) for k, v in demand_cfg["month_multipliers"].items()}

    # Public holiday multiplier
    ph_mult = float(demand_cfg["public_holiday_multiplier"])

    # Noise
    noise_std = float(demand_cfg["daily_noise_std"])

    # Base index
    base_mean = float(demand_cfg["base_daily_index"]["mean"])
    base_std = float(demand_cfg["base_daily_index"]["std"])

    rows: List[Dict[str, Any]] = []
    current = start_date

    while current <= end_date:
        cal = calendar_map[current]
        dow = int(cal["day_of_week"])
        is_ph = bool(cal["is_public_holiday"])
        is_weekend = bool(cal["is_weekend"])
        is_school = bool(cal["is_school_term"])
        is_peak = bool(cal["is_retail_peak"])

        for _, store in stores_df.iterrows():
            store_id = int(store["store_id"])
            size_band = store["size_band"]
            sf = size_factor.get(size_band, 1.0)

            # Base index for this store
            base = rng.normal(base_mean, base_std) * sf

            # Apply day-of-week multiplier
            base *= dow_mult.get(dow, 1.0)

            # Apply month multiplier
            base *= month_mult.get(current.month, 1.0)

            # Public holiday uplift
            if is_ph:
                base *= ph_mult

            # School holiday / retail peak uplift
            if is_peak and not is_ph:
                base *= 1.15

            # Random noise
            base *= rng.normal(1.0, noise_std)

            demand_index = max(0.0, base)

            # Convert to transaction count (roughly 1 transaction per index point)
            transaction_count = int(round(demand_index))

            # Sales amount: average basket ~$35–$55
            avg_basket = rng.uniform(35.0, 55.0)
            sales_amount = transaction_count * avg_basket

            rows.append(
                {
                    "store_id": store_id,
                    "date": current.isoformat(),
                    "day_of_week": dow,
                    "is_weekend": is_weekend,
                    "is_public_holiday": is_ph,
                    "is_school_term": is_school,
                    "is_retail_peak": is_peak,
                    "demand_index": round(demand_index, 2),
                    "transaction_count": transaction_count,
                    "sales_amount": round(sales_amount, 2),
                }
            )

        current += dt.timedelta(days=1)

    df = pd.DataFrame(rows)
    validate_all(df, DEMAND_SCHEMA, context="demand")
    return df