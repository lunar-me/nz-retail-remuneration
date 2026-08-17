"""Metric calculation layer for the integrated scorecard.

Computes meaningful health metrics by combining outputs from the leave,
remuneration, and capacity engines.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from src.capacity.capacity import CapacityPlanner
from src.leave_engine.balance import LeaveBalanceCalculator
from src.remuneration.costing import RemunerationCostingEngine

from .models import ProgrammeMetric, StoreMetric


class MetricCalculator:
    """Computes scorecard metrics from synthetic data and engine outputs."""

    # Thresholds for metric health status
    THRESHOLDS = {
        "avg_leave_balance_days": {"warning": 30.0, "critical": 50.0},
        "capacity_ratio": {"warning": 0.9, "critical": 0.8},
        "insurance_takeup_pct": {"warning": 0.40, "critical": 0.30},
        "flexibility_utilisation": {"warning": 0.40, "critical": 0.30},
    }

    def __init__(self):
        """Initialise the metric calculator."""

    # ------------------------------------------------------------------
    # Programme-level metrics
    # ------------------------------------------------------------------
    def programme_metrics(
        self,
        employees_df: pd.DataFrame,
        leave_types_df: pd.DataFrame,
        leave_tx_df: pd.DataFrame,
        remuneration_df: pd.DataFrame,
        *,
        as_of: Optional[dt.date] = None,
    ) -> "List[ProgrammeMetric]":
        """Compute programme-level health metrics.

        Parameters
        ----------
        employees_df : pd.DataFrame
            The ``employees`` table.
        leave_types_df : pd.DataFrame
            The ``leave_types`` table.
        leave_tx_df : pd.DataFrame
            The ``leave_transactions`` table.
        remuneration_df : pd.DataFrame
            The ``remuneration_components`` table.
        as_of : Optional[dt.date]
            As-of date for leave balance calculations.

        Returns
        -------
        List[ProgrammeMetric]
            Programme-level metrics.
        """
        from .models import ProgrammeMetric

        as_of = as_of or dt.date.today()
        metrics: List[ProgrammeMetric] = []

        # 1. Leave liability (avg annual leave balance in days)
        calc = LeaveBalanceCalculator(as_of=as_of)
        summary = calc.current_balances_summary(
            employees_df, leave_types_df, leave_tx_df
        )
        annual = summary[summary["leave_code"] == "ANNUAL"]
        avg_annual_balance_days = (
            float(annual["balance_days"].mean()) if len(annual) > 0 else 0.0
        )
        metrics.append(
            ProgrammeMetric(
                metric_name="avg_annual_leave_balance_days",
                metric_value=round(avg_annual_balance_days, 1),
                metric_unit="days",
                is_good=avg_annual_balance_days < self.THRESHOLDS["avg_leave_balance_days"]["warning"],
                status=_status_for_value(
                    avg_annual_balance_days,
                    self.THRESHOLDS["avg_leave_balance_days"],
                    higher_is_better=False,
                ),
                notes="Average annual leave balance across all employees",
            )
        )

        # 2. Insurance take-up rate
        insurance_rate = float(employees_df["insurance_enrolled"].mean())
        metrics.append(
            ProgrammeMetric(
                metric_name="insurance_takeup_rate",
                metric_value=round(insurance_rate, 3),
                metric_unit="pct",
                is_good=insurance_rate >= self.THRESHOLDS["insurance_takeup_pct"]["warning"],
                status=_status_for_value(
                    insurance_rate,
                    self.THRESHOLDS["insurance_takeup_pct"],
                    higher_is_better=True,
                ),
                notes="Percentage of employees enrolled in employer insurance",
            )
        )

        # 3. Average flexibility preference
        avg_flex = float(employees_df["flexibility_preference"].mean())
        metrics.append(
            ProgrammeMetric(
                metric_name="avg_flexibility_preference",
                metric_value=round(avg_flex, 3),
                metric_unit="score",
                is_good=avg_flex >= self.THRESHOLDS["flexibility_utilisation"]["warning"],
                status=_status_for_value(
                    avg_flex,
                    self.THRESHOLDS["flexibility_utilisation"],
                    higher_is_better=True,
                ),
                notes="Average employee flexibility preference (0–1)",
            )
        )

        # 4. Fully-loaded cost metrics
        costing = RemunerationCostingEngine()
        cost_summary = costing.cost_summary(remuneration_df, employees_df)
        total_annual = costing.total_annual_cost(cost_summary)
        avg_rate = float(cost_summary["fully_loaded_cost_per_hour"].mean())
        metrics.append(
            ProgrammeMetric(
                metric_name="total_annual_cost",
                metric_value=round(total_annual, 0),
                metric_unit="$",
                is_good=True,
                status="OK",
                notes="Total fully-loaded annual remuneration cost",
            )
        )
        metrics.append(
            ProgrammeMetric(
                metric_name="avg_fully_loaded_rate",
                metric_value=round(avg_rate, 2),
                metric_unit="$/hr",
                is_good=True,
                status="OK",
                notes="Average fully-loaded cost per hour",
            )
        )

        # 5. Workforce composition
        ft = int((employees_df["employment_type"] == "full_time").sum())
        pt = int((employees_df["employment_type"] == "part_time").sum())
        casual = int((employees_df["employment_type"] == "casual").sum())
        total = len(employees_df)
        metrics.append(
            ProgrammeMetric(
                metric_name="headcount",
                metric_value=float(total),
                metric_unit="employees",
                is_good=True,
                status="OK",
                notes=f"FT={ft} ({ft/total*100:.0f}%), PT={pt} ({pt/total*100:.0f}%), Casual={casual} ({casual/total*100:.0f}%)",
            )
        )

        return metrics

    # ------------------------------------------------------------------
    # Store-level metrics
    # ------------------------------------------------------------------
    def store_metrics(
        self,
        employees_df: pd.DataFrame,
        stores_df: pd.DataFrame,
        leave_types_df: pd.DataFrame,
        leave_tx_df: pd.DataFrame,
        demand_df: pd.DataFrame,
        rosters_df: pd.DataFrame,
        *,
        as_of: Optional[dt.date] = None,
        store_ids: Optional[List[int]] = None,
    ) -> "List[StoreMetric]":
        """Compute store-level health metrics.

        Parameters
        ----------
        employees_df : pd.DataFrame
            The ``employees`` table.
        stores_df : pd.DataFrame
            The ``stores`` table.
        leave_types_df : pd.DataFrame
            The ``leave_types`` table.
        leave_tx_df : pd.DataFrame
            The ``leave_transactions`` table.
        demand_df : pd.DataFrame
            The ``demand`` table.
        rosters_df : pd.DataFrame
            The ``rosters`` table.
        as_of : Optional[dt.date]
            As-of date for leave balances.
        store_ids : Optional[List[int]]
            If provided, only these stores.

        Returns
        -------
        List[StoreMetric]
            Store-level metrics.
        """
        from .models import StoreMetric

        as_of = as_of or dt.date.today()
        store_ids = store_ids or stores_df["store_id"].unique().tolist()
        metrics: List[StoreMetric] = []

        # Compute capacity gaps for a representative recent week
        end = min(as_of, dt.date(2026, 6, 30))
        start = end - dt.timedelta(days=6)

        planner = CapacityPlanner()
        demand_range = demand_df[
            (demand_df["date"] >= start.isoformat())
            & (demand_df["date"] <= end.isoformat())
        ]
        required = planner.compute_required_hours(demand_range)
        available = planner.compute_available_hours(
            employees_df, leave_tx_df, start, end,
            store_ids=store_ids, rosters_df=rosters_df,
        )
        gaps = planner.compute_capacity_gaps(required, available)
        gaps_df = planner.gaps_to_dataframe(gaps)

        for store_id in store_ids:
            store_df = employees_df[employees_df["store_id"] == store_id]
            if len(store_df) == 0:
                continue

            # Store headcount
            metrics.append(StoreMetric(
                store_id=store_id,
                metric_name="headcount",
                metric_value=float(len(store_df)),
                metric_unit="employees",
                is_good=True,
                status="OK",
            ))

            # Insurance take-up
            insurance = float(store_df["insurance_enrolled"].mean())
            metrics.append(StoreMetric(
                store_id=store_id,
                metric_name="insurance_takeup",
                metric_value=round(insurance, 3),
                metric_unit="pct",
                is_good=insurance >= self.THRESHOLDS["insurance_takeup_pct"]["warning"],
                status=_status_for_value(
                    insurance,
                    self.THRESHOLDS["insurance_takeup_pct"],
                    higher_is_better=True,
                ),
            ))

            # Avg flexibility
            avg_flex = float(store_df["flexibility_preference"].mean())
            metrics.append(StoreMetric(
                store_id=store_id,
                metric_name="avg_flexibility",
                metric_value=round(avg_flex, 3),
                metric_unit="score",
                is_good=avg_flex >= self.THRESHOLDS["flexibility_utilisation"]["warning"],
                status=_status_for_value(
                    avg_flex,
                    self.THRESHOLDS["flexibility_utilisation"],
                    higher_is_better=True,
                ),
            ))

            # Capacity ratio from gap analysis
            if len(gaps_df) > 0 and "store_id" in gaps_df.columns:
                store_gaps = gaps_df[gaps_df["store_id"] == store_id]
                if len(store_gaps) > 0:
                    total_req = float(store_gaps["required_hours"].sum())
                    total_avail = float(store_gaps["available_hours"].sum())
                    ratio = total_avail / total_req if total_req > 0 else 1.0
                    under_days = int((store_gaps["status"] == "UNDER_CAPACITY").sum())

                    metrics.append(StoreMetric(
                        store_id=store_id,
                        metric_name="capacity_ratio",
                        metric_value=round(ratio, 2),
                        metric_unit="ratio",
                        is_good=ratio >= self.THRESHOLDS["capacity_ratio"]["warning"],
                        status=_status_for_value(
                            ratio,
                            self.THRESHOLDS["capacity_ratio"],
                            higher_is_better=True,
                        ),
                        notes=f"{under_days} under-capacity days in last 7 days",
                    ))
            else:
                metrics.append(StoreMetric(
                    store_id=store_id,
                    metric_name="capacity_ratio",
                    metric_value=1.0,
                    metric_unit="ratio",
                    is_good=True,
                    status="OK",
                    notes="No demand data available for capacity analysis",
                ))

            # Store is tight capacity (edge case flag)
            is_tight = bool(
                stores_df[
                    (stores_df["store_id"] == store_id) &
                    (stores_df["is_tight_capacity"] == True)
                ].shape[0] > 0
            )
            if is_tight:
                metrics.append(StoreMetric(
                    store_id=store_id,
                    metric_name="tight_capacity_store",
                    metric_value=1.0,
                    metric_unit="flag",
                    is_good=False,
                    status="WARNING",
                    notes="Store flagged as structurally tight on capacity",
                ))

        return metrics


def _status_for_value(
    value: float,
    thresholds: dict,
    *,
    higher_is_better: bool,
) -> str:
    """Determine status (OK/WARNING/CRITICAL) for a metric value."""
    warning = thresholds.get("warning")
    critical = thresholds.get("critical")
    if warning is None:
        return "OK"

    if higher_is_better:
        if value >= warning:
            return "OK"
        if critical is not None and value >= critical:
            return "WARNING"
        return "CRITICAL"
    else:
        if value <= warning:
            return "OK"
        if critical is not None and value <= critical:
            return "WARNING"
        return "CRITICAL"