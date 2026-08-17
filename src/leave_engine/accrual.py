"""Leave accrual engine.

Computes weekly accruals, tracks running balances, and handles eligibility
rules, pro-rating, and balance caps. Built to operate on the synthetic
data layer's leave transaction history.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .holidays_act import HolidaysActRules
from .models import Employee, LeaveBalance, LeaveType, LeaveTransaction


@dataclass
class AccrualResult:
    """Result of a leave accrual/balance calculation."""

    balances: Dict[str, LeaveBalance]  # leave_code -> balance
    transactions: List[LeaveTransaction]
    messages: List[str] = None  # type: ignore[assignment]


class LeaveAccrualEngine:
    """Core leave accrual and balance engine.

    Operates on synthetic data tables (employees, leave_types,
    leave_transactions) to compute current leave balances with
    Holidays Act-oriented rules.
    """

    # Leave codes that accrue over time
    ACCRUAL_LEAVE_CODES = {"ANNUAL", "SICK", "BEREAVEMENT"}

    # Leave codes that are event-driven (no standing accrual)
    EVENT_LEAVE_CODES = {"PUBLIC_HOLIDAY", "ALTERNATIVE", "PARENTAL"}

    def __init__(
        self,
        rules: Optional[HolidaysActRules] = None,
        *,
        as_of: Optional[dt.date] = None,
    ):
        """Initialise the engine.

        Parameters
        ----------
        rules : Optional[HolidaysActRules]
            Rules wrapper. If ``None``, statutory defaults are used.
        as_of : Optional[dt.date]
            The as-of date for balance calculations. Defaults to today.
        """
        self.rules = rules or HolidaysActRules()
        self.as_of = as_of or dt.date.today()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_leave_types(self, leave_types_df: pd.DataFrame) -> Dict[str, LeaveType]:
        """Load the leave-types reference table into typed objects.

        Parameters
        ----------
        leave_types_df : pd.DataFrame
            The ``leave_types`` table from the synthetic data layer.

        Returns
        -------
        Dict[str, LeaveType]
            Mapping of leave code → LeaveType.
        """
        result: Dict[str, LeaveType] = {}
        for _, row in leave_types_df.iterrows():
            result[row["leave_code"]] = LeaveType(
                code=row["leave_code"],
                name=row["leave_name"],
                is_paid=bool(row["is_paid"]),
                carries_over=bool(row["carries_over"]),
                accrual_rate_hours_per_week=(
                    float(row["accrual_rate_hours_per_week"])
                    if pd.notna(row.get("accrual_rate_hours_per_week"))
                    else None
                ),
                accrual_rate_days_per_year=(
                    float(row["accrual_rate_days_per_year"])
                    if pd.notna(row.get("accrual_rate_days_per_year"))
                    else None
                ),
                max_balance_weeks=(
                    float(row["max_balance_weeks"])
                    if pd.notna(row.get("max_balance_weeks"))
                    else None
                ),
                max_balance_days=(
                    float(row["max_balance_days"])
                    if pd.notna(row.get("max_balance_days"))
                    else None
                ),
            )
        return result

    def load_employees(self, employees_df: pd.DataFrame) -> Dict[int, Employee]:
        """Load the employees table into typed objects.

        Parameters
        ----------
        employees_df : pd.DataFrame
            The ``employees`` table from the synthetic data layer.

        Returns
        -------
        Dict[int, Employee]
            Mapping of employee_id → Employee.
        """
        result: Dict[int, Employee] = {}
        for _, row in employees_df.iterrows():
            result[int(row["employee_id"])] = Employee(
                employee_id=int(row["employee_id"]),
                store_id=int(row["store_id"]),
                employment_type=row["employment_type"],
                start_date=dt.date.fromisoformat(row["start_date"]),
                contracted_hours_per_week=float(row["contracted_hours_per_week"]),
                role=row.get("role", ""),
                job_family=row.get("job_family", ""),
                is_high_leave_balance=bool(row.get("is_high_leave_balance", False)),
                is_new_starter=bool(row.get("is_new_starter", False)),
            )
        return result

    def calculate_balances(
        self,
        employees_df: pd.DataFrame,
        leave_types_df: pd.DataFrame,
        leave_transactions_df: pd.DataFrame,
        *,
        employee_ids: Optional[List[int]] = None,
    ) -> Dict[int, Dict[str, LeaveBalance]]:
        """Calculate current leave balances for all (or selected) employees.

        Parameters
        ----------
        employees_df : pd.DataFrame
            The ``employees`` table.
        leave_types_df : pd.DataFrame
            The ``leave_types`` table.
        leave_transactions_df : pd.DataFrame
            The ``leave_transactions`` table.
        employee_ids : Optional[List[int]]
            If provided, only these employees are processed.

        Returns
        -------
        Dict[int, Dict[str, LeaveBalance]]
            Mapping of employee_id → {leave_code → LeaveBalance}.
        """
        employees = self.load_employees(employees_df)
        leave_types = self.load_leave_types(leave_types_df)

        # Parse transactions, sorted by employee, leave code, date
        txs = self._parse_transactions(leave_transactions_df)

        # Filter to selected employees
        if employee_ids is not None:
            id_set = set(employee_ids)
            employees = {k: v for k, v in employees.items() if k in id_set}

        # Replay transactions to compute balances
        result: Dict[int, Dict[str, LeaveBalance]] = {}
        for emp_id, emp in employees.items():
            emp_txs = txs.get(emp_id, [])
            balances = self._compute_balances_for_employee(emp, emp_txs, leave_types)
            result[emp_id] = balances

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _parse_transactions(
        self, df: pd.DataFrame
    ) -> Dict[int, List[LeaveTransaction]]:
        """Parse the transactions table into typed, sorted objects."""
        result: Dict[int, List[LeaveTransaction]] = {}
        for _, row in df.iterrows():
            emp_id = int(row["employee_id"])
            tx = LeaveTransaction(
                employee_id=emp_id,
                leave_code=row["leave_code"],
                transaction_date=dt.date.fromisoformat(row["transaction_date"]),
                transaction_type=row["transaction_type"],
                hours=float(row["hours"]),
                balance_after=float(row["balance_after"]),
                reason_code=row.get("reason_code"),
            )
            result.setdefault(emp_id, []).append(tx)

        # Sort each employee's transactions chronologically
        for emp_id in result:
            result[emp_id].sort(key=lambda t: (t.transaction_date, t.transaction_type))
        return result

    def _compute_balances_for_employee(
        self,
        emp: Employee,
        txs: List[LeaveTransaction],
        leave_types: Dict[str, LeaveType],
    ) -> Dict[str, LeaveBalance]:
        """Replay transactions to compute the employee's leave balances.

        This uses the transaction history from the synthetic data. If a
        transaction is missing (e.g. new starter without history), accrual
        is computed from the employee's start date.
        """
        balances: Dict[str, LeaveBalance] = {}

        # Initialise balances for accrual-based leave types
        for code in self.ACCRUAL_LEAVE_CODES:
            if code in leave_types:
                balances[code] = LeaveBalance(
                    employee_id=emp.employee_id,
                    leave_code=code,
                )

        # Replay transactions in chronological order
        for tx in txs:
            if tx.leave_code not in balances:
                # Event-driven leave types
                balances[tx.leave_code] = LeaveBalance(
                    employee_id=emp.employee_id,
                    leave_code=tx.leave_code,
                )

            bal = balances[tx.leave_code]
            if tx.transaction_type == "ACCRUAL":
                bal.balance_hours += tx.hours
                bal.accrued_hours += tx.hours
            elif tx.transaction_type == "TAKEN":
                bal.balance_hours -= tx.hours
                bal.taken_hours += tx.hours
            bal.last_updated = tx.transaction_date
            bal.history.append(tx)

        # For employees without full transaction history, compute
        # expected accrual from start date to as_of
        self._fill_missing_accrual(emp, balances, leave_types)

        return balances

    def _fill_missing_accrual(
        self,
        emp: Employee,
        balances: Dict[str, LeaveBalance],
        leave_types: Dict[str, LeaveType],
    ) -> None:
        """Fill in accrual for employees with incomplete transaction history.

        For new starters or employees without recorded accrual transactions,
        compute the expected accrual from their start date to ``as_of``.
        """
        # Only handle annual and sick leave
        for code in ("ANNUAL", "SICK"):
            if code not in balances or code not in leave_types:
                continue

            bal = balances[code]
            lt = leave_types[code]

            # If the employee has no accrual history, compute from start date
            if bal.accrued_hours == 0.0:
                # Check eligibility
                if code == "ANNUAL":
                    if not self.rules.is_eligible_for_annual_leave(emp.start_date, self.as_of):
                        continue
                    weekly = self.rules.weekly_annual_leave_accrual_hours(
                        emp.contracted_hours_per_week
                    )
                else:  # SICK
                    if not self.rules.is_eligible_for_sick_leave(emp.start_date, self.as_of):
                        continue
                    weekly = self.rules.weekly_sick_leave_accrual_hours(
                        emp.contracted_hours_per_week
                    )

                # Compute weeks from start (or generation start) to as_of
                start = max(emp.start_date, dt.date(2024, 7, 1))
                weeks = max(0.0, (self.as_of - start).days / 7.0)
                accrued = weekly * weeks

                # Cap at max balance
                if code == "ANNUAL":
                    max_balance = self.rules.max_annual_balance_hours()
                else:
                    max_balance = self.rules.max_sick_balance_hours()
                accrued = min(accrued, max_balance)

                bal.balance_hours += accrued
                bal.accrued_hours += accrued
                bal.last_updated = self.as_of

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------
    def explain_balance(
        self,
        emp: Employee,
        balances: Dict[str, LeaveBalance],
        leave_types: Dict[str, LeaveType],
    ) -> List[str]:
        """Return a human-readable explanation of an employee's balances.

        Parameters
        ----------
        emp : Employee
            The employee.
        balances : Dict[str, LeaveBalance]
            The employee's computed balances.
        leave_types : Dict[str, LeaveType]
            Leave type definitions.

        Returns
        -------
        List[str]
            Explanation lines.
        """
        lines = [
            f"Employee {emp.employee_id} — {emp.role} ({emp.employment_type})",
            f"Start date: {emp.start_date}",
            f"Contracted hours: {emp.contracted_hours_per_week}h/week",
            "",
        ]

        for code, bal in sorted(balances.items()):
            lt = leave_types.get(code)
            name = lt.name if lt else code
            lines.append(f"  {name} ({code}): {bal.balance_hours:.1f} hours ({bal.balance_days:.1f} days)")
            lines.append(f"    Accrued: {bal.accrued_hours:.1f}h | Taken: {bal.taken_hours:.1f}h")

            # Pay method note
            pay_method = self.rules.pay_method_for(emp.employment_type)
            lines.append(f"    Pay method: {pay_method.method}")
            lines.append("")

        return lines