"""Remuneration costing engine.

Computes fully-loaded hourly and annual costs from the synthetic
remuneration_components table, with breakdown by component and
aggregation by store, role, and employment type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from .models import CostAssumptions, EmployeeCostProfile, RemunerationComponents


class RemunerationCostingEngine:
    """Computes fully-loaded costs from the synthetic remuneration data."""

    def __init__(self, assumptions: Optional[CostAssumptions] = None):
        """Initialise the costing engine.

        Parameters
        ----------
        assumptions : Optional[CostAssumptions]
            Cost assumptions. If ``None``, defaults are used.
        """
        self.assumptions = assumptions or CostAssumptions()

    # ------------------------------------------------------------------
    # Load & build profiles
    # ------------------------------------------------------------------
    def load_components(
        self,
        remuneration_df: pd.DataFrame,
        employees_df: pd.DataFrame,
    ) -> Dict[int, RemunerationComponents]:
        """Build RemunerationComponents objects from synthetic tables.

        Parameters
        ----------
        remuneration_df : pd.DataFrame
            The ``remuneration_components`` table.
        employees_df : pd.DataFrame
            The ``employees`` table.

        Returns
        -------
        Dict[int, RemunerationComponents]
            Mapping of employee_id → components.
        """
        emp_lookup = {
            int(row["employee_id"]): row.to_dict()
            for _, row in employees_df.iterrows()
        }

        components: Dict[int, RemunerationComponents] = {}
        for _, row in remuneration_df.iterrows():
            emp_id = int(row["employee_id"])
            emp = emp_lookup.get(emp_id, {})

            components[emp_id] = RemunerationComponents(
                employee_id=emp_id,
                base_hourly_rate=float(row["base_hourly_rate"]),
                contracted_hours_per_week=float(
                    emp.get("contracted_hours_per_week", 0.0)
                ),
                employment_type=emp.get("employment_type", "full_time"),
                kiwisaver_employer_rate=float(row["kiwisaver_employer_rate"]),
                leave_loading_rate=float(row["leave_loading_rate"]),
                insurance_monthly_cost=float(row["insurance_monthly_cost"]),
                flexibility_premium_rate=float(row["flexibility_premium_rate"]),
            )
        return components

    # ------------------------------------------------------------------
    # Costing calculations
    # ------------------------------------------------------------------
    def compute_cost_profile(
        self,
        components: RemunerationComponents,
    ) -> EmployeeCostProfile:
        """Compute the cost profile for an employee's components.

        Parameters
        ----------
        components : RemunerationComponents
            The employee's remuneration components.

        Returns
        -------
        EmployeeCostProfile
            The computed cost profile.
        """
        return EmployeeCostProfile(
            employee_id=components.employee_id,
            components=components,
        )

    def compute_all_profiles(
        self,
        remuneration_df: pd.DataFrame,
        employees_df: pd.DataFrame,
    ) -> Dict[int, EmployeeCostProfile]:
        """Compute cost profiles for all employees.

        Parameters
        ----------
        remuneration_df : pd.DataFrame
            The ``remuneration_components`` table.
        employees_df : pd.DataFrame
            The ``employees`` table.

        Returns
        -------
        Dict[int, EmployeeCostProfile]
            Mapping of employee_id → cost profile.
        """
        components_map = self.load_components(remuneration_df, employees_df)
        return {
            emp_id: self.compute_cost_profile(comp)
            for emp_id, comp in components_map.items()
        }

    # ------------------------------------------------------------------
    # Summary tables
    # ------------------------------------------------------------------
    def cost_summary(
        self,
        remuneration_df: pd.DataFrame,
        employees_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Return a per-employee cost summary DataFrame.

        Parameters
        ----------
        remuneration_df : pd.DataFrame
            The ``remuneration_components`` table.
        employees_df : pd.DataFrame
            The ``employees`` table.

        Returns
        -------
        pd.DataFrame
            One row per employee with fully-loaded costs and breakdown.
        """
        profiles = self.compute_all_profiles(remuneration_df, employees_df)
        emp_lookup = {
            int(row["employee_id"]): row.to_dict()
            for _, row in employees_df.iterrows()
        }

        rows = []
        for emp_id, profile in profiles.items():
            comp = profile.components
            emp = emp_lookup.get(emp_id, {})

            rows.append(
                {
                    "employee_id": emp_id,
                    "store_id": emp.get("store_id", 0),
                    "role": emp.get("role", ""),
                    "employment_type": emp.get("employment_type", ""),
                    "base_hourly_rate": round(comp.base_hourly_rate, 2),
                    "kiwisaver_cost_per_hour": round(comp.kiwisaver_cost_per_hour, 2),
                    "leave_loading_cost_per_hour": round(comp.leave_loading_cost_per_hour, 2),
                    "insurance_cost_per_hour": round(comp.insurance_cost_per_hour, 2),
                    "flexibility_cost_per_hour": round(comp.flexibility_cost_per_hour, 2),
                    "fully_loaded_cost_per_hour": round(comp.fully_loaded_cost_per_hour, 2),
                    "contracted_hours_per_week": comp.contracted_hours_per_week,
                    "weekly_cost": round(comp.weekly_cost, 2),
                    "annual_cost": round(comp.annual_cost, 2),
                }
            )
        return pd.DataFrame(rows)

    def aggregate_by(
        self,
        cost_summary: pd.DataFrame,
        group_cols: List[str],
    ) -> pd.DataFrame:
        """Aggregate cost summary by the given columns.

        Parameters
        ----------
        cost_summary : pd.DataFrame
            Output of :meth:`cost_summary`.
        group_cols : List[str]
            Columns to group by.

        Returns
        -------
        pd.DataFrame
            Aggregated summary with headcount, total annual cost, avg rates.
        """
        if not group_cols:
            group_cols = []

        result = cost_summary.groupby(group_cols, dropna=False).agg(
            headcount=("employee_id", "count"),
            avg_base_rate=("base_hourly_rate", "mean"),
            avg_fully_loaded_rate=("fully_loaded_cost_per_hour", "mean"),
            total_weekly_cost=("weekly_cost", "sum"),
            total_annual_cost=("annual_cost", "sum"),
        ).reset_index()

        return result

    def total_annual_cost(
        self,
        cost_summary: pd.DataFrame,
    ) -> float:
        """Return the total annual fully-loaded cost for all employees.

        Parameters
        ----------
        cost_summary : pd.DataFrame
            Output of :meth:`cost_summary`.

        Returns
        -------
        float
            Total annual cost.
        """
        return float(cost_summary["annual_cost"].sum())

    def cost_breakdown(
        self,
        cost_summary: pd.DataFrame,
    ) -> Dict[str, float]:
        """Return the annual cost breakdown by component.

        Parameters
        ----------
        cost_summary : pd.DataFrame
            Output of :meth:`cost_summary`.

        Returns
        -------
        Dict[str, float]
            Annual cost per component category.
        """
        hours_per_year = 52.0 * cost_summary["contracted_hours_per_week"]
        return {
            "base_pay": float((cost_summary["base_hourly_rate"] * hours_per_year).sum()),
            "kiwisaver": float((cost_summary["kiwisaver_cost_per_hour"] * hours_per_year).sum()),
            "leave_loading": float((cost_summary["leave_loading_cost_per_hour"] * hours_per_year).sum()),
            "insurance": float((cost_summary["insurance_cost_per_hour"] * hours_per_year).sum()),
            "flexibility": float((cost_summary["flexibility_cost_per_hour"] * hours_per_year).sum()),
            "total": float(cost_summary["annual_cost"].sum()),
        }