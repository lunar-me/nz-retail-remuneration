"""Capacity planning engine.

Converts demand into required labour hours, computes available hours
(after leave), and identifies capacity gaps by store, day, and role.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from .demand_forecast import DemandForecaster, DemandProfile
from .labour_standards import LabourStandards
from .models import AvailableHours, CapacityGap, LabourRequirement


class CapacityPlanner:
    """Computes capacity gaps from demand and workforce data."""

    # Gap status thresholds
    UNDER_THRESHOLD = 0.9   # available < 90% of required → under-capacity
    OVER_THRESHOLD = 1.15   # available > 115% of required → over-capacity

    def __init__(
        self,
        labour_standards: Optional[LabourStandards] = None,
        forecaster: Optional[DemandForecaster] = None,
    ):
        """Initialise the capacity planner.

        Parameters
        ----------
        labour_standards : Optional[LabourStandards]
            Labour productivity standards. If ``None``, defaults used.
        forecaster : Optional[DemandForecaster]
            Demand forecaster. If ``None``, a default is created.
        """
        self.labour = labour_standards or LabourStandards()
        self.forecaster = forecaster or DemandForecaster()

    # ------------------------------------------------------------------
    # Required hours from demand
    # ------------------------------------------------------------------
    def compute_required_hours(
        self,
        demand_df: pd.DataFrame,
        roles: Optional[List[str]] = None,
    ) -> List[LabourRequirement]:
        """Compute required labour hours from demand.

        Uses a default role mix based on each store's employee profile.
        For simplicity, demand is allocated across all active roles
        proportional to the store's employee role distribution.

        Parameters
        ----------
        demand_df : pd.DataFrame
            The ``demand`` table.
        roles : Optional[List[str]]
            If provided, only these roles are computed. Otherwise, all
            standard roles are used.

        Returns
        -------
        List[LabourRequirement]
            Required hours per store-day-role.
        """
        default_roles = roles or [
            "Checkout / Front End",
            "Grocery / Nightfill",
            "Fresh Foods",
            "Online / Click & Collect",
            "Department Supervisor",
            "Store Management",
            "Other / Support",
        ]

        # Role weighting: front-line roles carry more of the demand
        role_weight = {
            "Checkout / Front End": 0.30,
            "Grocery / Nightfill": 0.18,
            "Fresh Foods": 0.16,
            "Online / Click & Collect": 0.10,
            "Department Supervisor": 0.12,
            "Store Management": 0.06,
            "Other / Support": 0.08,
        }

        requirements: List[LabourRequirement] = []
        for _, row in demand_df.iterrows():
            store_id = int(row["store_id"])
            date = _to_date(row["date"])
            demand_index = float(row["demand_index"])

            # Allocate demand across roles using weighted split
            # (front-line roles carry more demand than back-office)
            for role in default_roles:
                weight = role_weight.get(role, 0.1)
                per_role_demand = demand_index * weight
                required = self.labour.required_hours(per_role_demand, role)
                requirements.append(
                    LabourRequirement(
                        store_id=store_id,
                        date=date,
                        role=role,
                        required_hours=required,
                        demand_index=per_role_demand,
                        productivity=self.labour.productivity_for_role(role),
                    )
                )
        return requirements

    # ------------------------------------------------------------------
    # Available hours
    # ------------------------------------------------------------------
    def compute_available_hours(
        self,
        employees_df: pd.DataFrame,
        leave_tx_df: pd.DataFrame,
        start: dt.date,
        end: dt.date,
        *,
        store_ids: Optional[List[int]] = None,
        rosters_df: Optional[pd.DataFrame] = None,
    ) -> List[AvailableHours]:
        """Compute available hours per employee per day.

        Available = contracted daily hours − leave hours on that day.
        If ``rosters_df`` is provided, employees are only considered
        available on days they are actually rostered to work.

        Parameters
        ----------
        employees_df : pd.DataFrame
            The ``employees`` table.
        leave_tx_df : pd.DataFrame
            The ``leave_transactions`` table.
        start : dt.date
            Inclusive start date.
        end : dt.date
            Inclusive end date.
        store_ids : Optional[List[int]]
            If provided, only these stores' employees are processed.
        rosters_df : Optional[pd.DataFrame]
            The ``rosters`` table. If provided, employees are only
            available on their rostered days.

        Returns
        -------
        List[AvailableHours]
            Available hours per employee-day.
        """
        # Build leave lookup: (employee_id, date) -> hours on leave
        leave_lookup: Dict[tuple, float] = {}
        for _, row in leave_tx_df.iterrows():
            emp_id = int(row["employee_id"])
            tx_date = _to_date(row["transaction_date"])
            if tx_date < start or tx_date > end:
                continue
            if row["transaction_type"] == "TAKEN":
                key = (emp_id, tx_date)
                leave_lookup[key] = leave_lookup.get(key, 0.0) + float(row["hours"])

        # Build roster lookup: (employee_id, date) -> hours rostered
        roster_lookup: Dict[tuple, float] = {}
        if rosters_df is not None:
            for _, row in rosters_df.iterrows():
                emp_id = int(row["employee_id"])
                work_date = _to_date(row["work_date"])
                if work_date < start or work_date > end:
                    continue
                key = (emp_id, work_date)
                roster_lookup[key] = roster_lookup.get(key, 0.0) + float(row["hours_worked"])

        result: List[AvailableHours] = []
        for _, emp in employees_df.iterrows():
            emp_id = int(emp["employee_id"])
            store_id = int(emp["store_id"])
            if store_ids is not None and store_id not in store_ids:
                continue

            contracted = float(emp["contracted_hours_per_week"])
            daily_contracted = contracted / 5.0  # assume 5-day week
            role = emp["role"]
            flexibility = float(emp.get("flexibility_preference", 0.0))
            emp_start = _to_date(emp["start_date"])

            current = start
            while current <= end:
                if current >= emp_start:
                    # If rosters provided, only count rostered days
                    if rosters_df is not None:
                        rostered = roster_lookup.get((emp_id, current), 0.0)
                        if rostered <= 0:
                            current += dt.timedelta(days=1)
                            continue
                        daily_contract = rostered
                    else:
                        daily_contract = daily_contracted

                    leave_hours = leave_lookup.get((emp_id, current), 0.0)
                    available = max(0.0, daily_contract - leave_hours)
                    if available > 0:
                        result.append(
                            AvailableHours(
                                employee_id=emp_id,
                                store_id=store_id,
                                date=current,
                                role=role,
                                contracted_hours=daily_contract,
                                leave_hours=leave_hours,
                                available_hours=available,
                                flexibility_preference=flexibility,
                            )
                        )
                current += dt.timedelta(days=1)

        return result

    # ------------------------------------------------------------------
    # Capacity gaps
    # ------------------------------------------------------------------
    def compute_capacity_gaps(
        self,
        required: List[LabourRequirement],
        available: List[AvailableHours],
    ) -> List[CapacityGap]:
        """Compute capacity gaps.

        Parameters
        ----------
        required : List[LabourRequirement]
            Required hours per store-day-role.
        available : List[AvailableHours]
            Available hours per employee-day.

        Returns
        -------
        List[CapacityGap]
            Capacity gaps per store-day-role.
        """
        # Aggregate available hours by store-day-role
        avail_by_key: Dict[tuple, float] = {}
        for a in available:
            key = (a.store_id, a.date, a.role)
            avail_by_key[key] = avail_by_key.get(key, 0.0) + a.available_hours

        gaps: List[CapacityGap] = []
        for req in required:
            key = (req.store_id, req.date, req.role)
            avail_hours = avail_by_key.get(key, 0.0)
            gap = req.required_hours - avail_hours
            ratio = (avail_hours / req.required_hours) if req.required_hours > 0 else 1.0

            if ratio < self.UNDER_THRESHOLD:
                status = "UNDER_CAPACITY"
            elif ratio > self.OVER_THRESHOLD:
                status = "OVER_CAPACITY"
            else:
                status = "BALANCED"

            gaps.append(
                CapacityGap(
                    store_id=req.store_id,
                    date=req.date,
                    role=req.role,
                    required_hours=req.required_hours,
                    available_hours=avail_hours,
                    gap_hours=gap,
                    gap_ratio=ratio,
                    status=status,
                )
            )
        return gaps

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def gaps_to_dataframe(self, gaps: List[CapacityGap]) -> pd.DataFrame:
        """Convert capacity gaps to a DataFrame for reporting.

        Parameters
        ----------
        gaps : List[CapacityGap]
            Capacity gaps.

        Returns
        -------
        pd.DataFrame
            Gap table.
        """
        rows = []
        for g in gaps:
            rows.append(
                {
                    "store_id": g.store_id,
                    "date": g.date.isoformat(),
                    "role": g.role,
                    "required_hours": round(g.required_hours, 1),
                    "available_hours": round(g.available_hours, 1),
                    "gap_hours": round(g.gap_hours, 1),
                    "gap_ratio": round(g.gap_ratio, 2),
                    "status": g.status,
                }
            )
        return pd.DataFrame(rows)

    def summarize_gaps(
        self,
        gaps_df: pd.DataFrame,
        group_cols: List[str],
    ) -> pd.DataFrame:
        """Summarize capacity gaps.

        Parameters
        ----------
        gaps_df : pd.DataFrame
            Output of :meth:`gaps_to_dataframe`.
        group_cols : List[str]
            Columns to group by.

        Returns
        -------
        pd.DataFrame
            Summarized gaps.
        """
        result = gaps_df.groupby(group_cols, dropna=False).agg(
            total_required=("required_hours", "sum"),
            total_available=("available_hours", "sum"),
            total_gap=("gap_hours", "sum"),
            under_capacity_days=("status", lambda s: (s == "UNDER_CAPACITY").sum()),
            over_capacity_days=("status", lambda s: (s == "OVER_CAPACITY").sum()),
            balanced_days=("status", lambda s: (s == "BALANCED").sum()),
        ).reset_index()
        result["avg_ratio"] = (result["total_available"] / result["total_required"]).round(2)
        return result


def _to_date(value) -> dt.date:
    """Convert a date-like value to a datetime.date object."""
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        return dt.date.fromisoformat(value)
    if isinstance(value, dt.datetime):
        return value.date()
    raise ValueError(f"Cannot convert {type(value)} to date")