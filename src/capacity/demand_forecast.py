"""Demand forecasting and profiling.

Computes expected demand from the synthetic demand series using weekly
profiles, and forecasts future demand based on day-of-week and month
seasonality patterns.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd


def _to_date(value) -> dt.date:
    """Convert a date-like value to a datetime.date object."""
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        return dt.date.fromisoformat(value)
    if isinstance(value, dt.datetime):
        return value.date()
    raise ValueError(f"Cannot convert {type(value)} to date")


@dataclass
class DemandProfile:
    """A store's demand profile."""

    store_id: int
    avg_daily_index: float
    day_of_week_multipliers: Dict[int, float]
    month_multipliers: Dict[int, float]
    weekend_ratio: float  # avg weekend / avg weekday


class DemandForecaster:
    """Forecasts demand using historical patterns."""

    def __init__(self):
        """Initialise the demand forecaster."""

    # ------------------------------------------------------------------
    # Historical profiling
    # ------------------------------------------------------------------
    def build_store_profiles(
        self,
        demand_df: pd.DataFrame,
    ) -> Dict[int, DemandProfile]:
        """Build demand profiles from historical data.

        Parameters
        ----------
        demand_df : pd.DataFrame
            The ``demand`` table from the synthetic data.

        Returns
        -------
        Dict[int, DemandProfile]
            Mapping of store_id → DemandProfile.
        """
        profiles: Dict[int, DemandProfile] = {}

        for store_id in demand_df["store_id"].unique():
            store_df = demand_df[demand_df["store_id"] == store_id].copy()

            # Ensure month column exists (derive from date if needed)
            if "month" not in store_df.columns:
                store_df["month"] = store_df["date"].apply(
                    lambda d: _to_date(d).month
                )

            avg_daily = float(store_df["demand_index"].mean())

            # Day-of-week multipliers (relative to average)
            dow_avg = store_df.groupby("day_of_week")["demand_index"].mean()
            dow_mult = {
                int(dow): float(avg / avg_daily) if avg_daily > 0 else 1.0
                for dow, avg in dow_avg.items()
            }

            # Month multipliers (relative to average)
            month_avg = store_df.groupby("month")["demand_index"].mean()
            month_mult = {
                int(month): float(avg / avg_daily) if avg_daily > 0 else 1.0
                for month, avg in month_avg.items()
            }

            # Weekend ratio
            weekend = store_df[store_df["is_weekend"] == True]["demand_index"]
            weekday = store_df[store_df["is_weekend"] == False]["demand_index"]
            weekend_ratio = (
                float(weekend.mean() / weekday.mean())
                if len(weekday) > 0 and weekday.mean() > 0
                else 1.0
            )

            profiles[store_id] = DemandProfile(
                store_id=store_id,
                avg_daily_index=avg_daily,
                day_of_week_multipliers=dow_mult,
                month_multipliers=month_mult,
                weekend_ratio=weekend_ratio,
            )

        return profiles

    # ------------------------------------------------------------------
    # Forecasting
    # ------------------------------------------------------------------
    def forecast_day(
        self,
        profile: DemandProfile,
        date: dt.date,
    ) -> float:
        """Forecast demand for a specific date.

        Parameters
        ----------
        profile : DemandProfile
            The store's demand profile.
        date : dt.date
            The date to forecast.

        Returns
        -------
        float
            Forecast demand index.
        """
        dow = date.weekday()  # 0=Mon ... 6=Sun
        month = date.month

        dow_mult = profile.day_of_week_multipliers.get(dow, 1.0)
        month_mult = profile.month_multipliers.get(month, 1.0)

        return profile.avg_daily_index * dow_mult * month_mult

    def forecast_period(
        self,
        profile: DemandProfile,
        start: dt.date,
        end: dt.date,
    ) -> pd.DataFrame:
        """Forecast demand for a date range.

        Parameters
        ----------
        profile : DemandProfile
            The store's demand profile.
        start : dt.date
            Inclusive start date.
        end : dt.date
            Inclusive end date.

        Returns
        -------
        pd.DataFrame
            Forecast demand per day.
        """
        rows = []
        current = start
        while current <= end:
            rows.append(
                {
                    "store_id": profile.store_id,
                    "date": current,
                    "day_of_week": current.weekday(),
                    "forecast_demand_index": round(
                        self.forecast_day(profile, current), 2
                    ),
                }
            )
            current += dt.timedelta(days=1)
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Exception detection
    # ------------------------------------------------------------------
    def identify_peaks(
        self,
        demand_df: pd.DataFrame,
        *,
        threshold_multiplier: float = 1.5,
    ) -> pd.DataFrame:
        """Identify demand peaks (days above threshold × store average).

        Parameters
        ----------
        demand_df : pd.DataFrame
            The ``demand`` table.
        threshold_multiplier : float, optional
            Days with demand > threshold × store average are flagged.

        Returns
        -------
        pd.DataFrame
            Peak-day rows.
        """
        profiles = self.build_store_profiles(demand_df)

        rows = []
        for store_id, profile in profiles.items():
            store_df = demand_df[demand_df["store_id"] == store_id].copy()
            threshold = profile.avg_daily_index * threshold_multiplier
            peaks = store_df[store_df["demand_index"] > threshold]
            if len(peaks) > 0:
                peaks = peaks.copy()
                peaks["is_peak"] = True
                peaks["threshold"] = threshold
                rows.append(peaks)
        if rows:
            return pd.concat(rows, ignore_index=True)
        return pd.DataFrame(
            columns=[
                "store_id", "date", "day_of_week", "is_weekend",
                "is_public_holiday", "demand_index", "is_peak", "threshold",
            ]
        )