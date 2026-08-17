"""Leave balance calculator and projection.

Provides higher-level balance computation, accrual projections into the
future, and balance-explanation reports.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .accrual import LeaveAccrualEngine
from .holidays_act import HolidaysActRules
from .models import Employee, LeaveBalance, LeaveExplanation, LeaveType


@dataclass
class ProjectedBalance:
    """A projected leave balance at a future date."""

    employee_id: int
    leave_code: str
    as_of: dt.date
    projected_hours: float
    weekly_accrual_hours: float
    notes: List[str] = None  # type: ignore[assignment]


class LeaveBalanceCalculator:
    """High-level balance calculations, projections, and explanations."""

    def __init__(
        self,
        engine: Optional[LeaveAccrualEngine] = None,
        *,
        as_of: Optional[dt.date] = None,
    ):
        """Initialise the balance calculator.

        Parameters
        ----------
        engine : Optional[LeaveAccrualEngine]
            The underlying accrual engine. If ``None``, a default is created.
        as_of : Optional[dt.date]
            The as-of date. Defaults to today.
        """
        self.as_of = as_of or dt.date.today()
        self.engine = engine or LeaveAccrualEngine(as_of=self.as_of)
        self.rules = self.engine.rules

    # ------------------------------------------------------------------
    # Current balances (summary)
    # ------------------------------------------------------------------
    def current_balances_summary(
        self,
        employees_df: pd.DataFrame,
        leave_types_df: pd.DataFrame,
        leave_transactions_df: pd.DataFrame,
        *,
        employee_ids: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Return a summary DataFrame of current leave balances.

        Parameters
        ----------
        employees_df : pd.DataFrame
            The ``employees`` table.
        leave_types_df : pd.DataFrame
            The ``leave_types`` table.
        leave_transactions_df : pd.DataFrame
            The ``leave_transactions`` table.
        employee_ids : Optional[List[int]]
            Optional filter.

        Returns
        -------
        pd.DataFrame
            Summary with one row per employee per leave code.
        """
        balances_map = self.engine.calculate_balances(
            employees_df,
            leave_types_df,
            leave_transactions_df,
            employee_ids=employee_ids,
        )
        employees = self.engine.load_employees(employees_df)

        rows = []
        for emp_id, balances in balances_map.items():
            emp = employees[emp_id]
            for code, bal in balances.items():
                rows.append(
                    {
                        "employee_id": emp_id,
                        "store_id": emp.store_id,
                        "employment_type": emp.employment_type,
                        "role": emp.role,
                        "leave_code": code,
                        "balance_hours": round(bal.balance_hours, 2),
                        "balance_days": round(bal.balance_days, 2),
                        "accrued_hours": round(bal.accrued_hours, 2),
                        "taken_hours": round(bal.taken_hours, 2),
                        "last_updated": bal.last_updated.isoformat() if bal.last_updated else None,
                        "is_high_leave_balance": emp.is_high_leave_balance,
                        "is_new_starter": emp.is_new_starter,
                    }
                )
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Projections
    # ------------------------------------------------------------------
    def project_balance(
        self,
        emp: Employee,
        balance: LeaveBalance,
        leave_type: LeaveType,
        *,
        as_of: dt.date,
        weeks_ahead: float = 52.0,
    ) -> ProjectedBalance:
        """Project a leave balance into the future.

        Parameters
        ----------
        emp : Employee
            The employee.
        balance : LeaveBalance
            The current balance.
        leave_type : LeaveType
            The leave type.
        as_of : dt.date
            The current as-of date.
        weeks_ahead : float, optional
            Number of weeks to project (default 52).

        Returns
        -------
        ProjectedBalance
            The projected balance.
        """
        # Determine weekly accrual rate
        if leave_type.code == "ANNUAL":
            weekly = self.rules.weekly_annual_leave_accrual_hours(
                emp.contracted_hours_per_week
            )
            max_hours = self.rules.max_annual_balance_hours()
        elif leave_type.code == "SICK":
            weekly = self.rules.weekly_sick_leave_accrual_hours(
                emp.contracted_hours_per_week
            )
            max_hours = self.rules.max_sick_balance_hours()
        elif leave_type.code == "BEREAVEMENT":
            weekly = self.rules.weekly_bereavement_accrual_hours(
                emp.contracted_hours_per_week
            )
            max_hours = float("inf")
        else:
            weekly = 0.0
            max_hours = float("inf")

        projected = balance.balance_hours + weekly * weeks_ahead
        projected = min(projected, max_hours)

        notes = []
        if projected >= max_hours and max_hours != float("inf"):
            notes.append(f"Capped at max balance of {max_hours:.0f} hours")

        return ProjectedBalance(
            employee_id=emp.employee_id,
            leave_code=leave_type.code,
            as_of=as_of + dt.timedelta(weeks=weeks_ahead),
            projected_hours=projected,
            weekly_accrual_hours=weekly,
            notes=notes,
        )

    def project_all_balances(
        self,
        employees_df: pd.DataFrame,
        leave_types_df: pd.DataFrame,
        leave_transactions_df: pd.DataFrame,
        *,
        weeks_ahead: float = 52.0,
        employee_ids: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Project all employee balances into the future.

        Parameters
        ----------
        employees_df : pd.DataFrame
            The ``employees`` table.
        leave_types_df : pd.DataFrame
            The ``leave_types`` table.
        leave_transactions_df : pd.DataFrame
            The ``leave_transactions`` table.
        weeks_ahead : float, optional
            Weeks to project (default 52).
        employee_ids : Optional[List[int]]
            Optional filter.

        Returns
        -------
        pd.DataFrame
            Projection summary.
        """
        balances_map = self.engine.calculate_balances(
            employees_df,
            leave_types_df,
            leave_transactions_df,
            employee_ids=employee_ids,
        )
        employees = self.engine.load_employees(employees_df)
        leave_types = self.engine.load_leave_types(leave_types_df)

        rows = []
        for emp_id, balances in balances_map.items():
            emp = employees[emp_id]
            for code, bal in balances.items():
                if code not in leave_types:
                    continue
                proj = self.project_balance(
                    emp, bal, leave_types[code],
                    as_of=self.as_of,
                    weeks_ahead=weeks_ahead,
                )
                rows.append(
                    {
                        "employee_id": emp_id,
                        "leave_code": code,
                        "current_balance_hours": round(bal.balance_hours, 2),
                        "projected_date": proj.as_of.isoformat(),
                        "projected_hours": round(proj.projected_hours, 2),
                        "weekly_accrual_hours": round(proj.weekly_accrual_hours, 4),
                        "notes": "; ".join(proj.notes) if proj.notes else "",
                    }
                )
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Explanations
    # ------------------------------------------------------------------
    def explain_balances(
        self,
        employees_df: pd.DataFrame,
        leave_types_df: pd.DataFrame,
        leave_transactions_df: pd.DataFrame,
        *,
        employee_ids: Optional[List[int]] = None,
    ) -> List[LeaveExplanation]:
        """Generate explanations for employee leave balances.

        Parameters
        ----------
        employees_df : pd.DataFrame
            The ``employees`` table.
        leave_types_df : pd.DataFrame
            The ``leave_types`` table.
        leave_transactions_df : pd.DataFrame
            The ``leave_transactions`` table.
        employee_ids : Optional[List[int]]
            Optional filter.

        Returns
        -------
        List[LeaveExplanation]
            Explanation objects.
        """
        balances_map = self.engine.calculate_balances(
            employees_df,
            leave_types_df,
            leave_transactions_df,
            employee_ids=employee_ids,
        )
        employees = self.engine.load_employees(employees_df)
        leave_types = self.engine.load_leave_types(leave_types_df)

        explanations: List[LeaveExplanation] = []
        for emp_id, balances in balances_map.items():
            emp = employees[emp_id]
            for code, bal in balances.items():
                lt = leave_types.get(code)
                lines = []
                lines.append(f"  Employment type: {emp.employment_type}")
                lines.append(f"  Contracted hours: {emp.contracted_hours_per_week}h/week")
                lines.append(f"  Start date: {emp.start_date}")

                # Eligibility
                if code == "ANNUAL":
                    eligible = self.rules.is_eligible_for_annual_leave(emp.start_date, self.as_of)
                    lines.append(f"  Annual leave eligible: {eligible}")
                    if not eligible:
                        months_to = self.rules.annual_leave_vesting_months - self.rules.months_between(emp.start_date, self.as_of)
                        lines.append(f"  Months to vesting: {max(0, months_to):.1f}")
                elif code == "SICK":
                    eligible = self.rules.is_eligible_for_sick_leave(emp.start_date, self.as_of)
                    lines.append(f"  Sick leave eligible: {eligible}")

                # Pay method
                pay_method = self.rules.pay_method_for(emp.employment_type)
                lines.append(f"  Pay method: {pay_method.method}")
                lines.append(f"    {pay_method.description}")

                # Accrual rate
                if code == "ANNUAL":
                    weekly = self.rules.weekly_annual_leave_accrual_hours(emp.contracted_hours_per_week)
                    lines.append(f"  Weekly accrual: {weekly:.4f} hours/week")
                elif code == "SICK":
                    weekly = self.rules.weekly_sick_leave_accrual_hours(emp.contracted_hours_per_week)
                    lines.append(f"  Weekly accrual: {weekly:.4f} hours/week")

                explanations.append(
                    LeaveExplanation(
                        employee_id=emp_id,
                        leave_code=code,
                        current_balance_hours=bal.balance_hours,
                        accrued_hours=bal.accrued_hours,
                        taken_hours=bal.taken_hours,
                        explanation_lines=lines,
                    )
                )
        return explanations

    def render_explanations_to_text(
        self,
        explanations: List[LeaveExplanation],
    ) -> str:
        """Render a list of explanations to readable text.

        Parameters
        ----------
        explanations : List[LeaveExplanation]
            Explanation objects.

        Returns
        -------
        str
            Formatted text output.
        """
        sections = [exp.to_text() for exp in explanations]
        return "\n\n" + "\n\n".join(sections) + "\n"