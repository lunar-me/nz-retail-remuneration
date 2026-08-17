"""Data models for the leave engine.

Defines dataclasses for leave types, employee eligibility, accrual rules,
and balances. These are the typed contracts used by the calculation logic.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class LeaveType:
    """A single leave type with its rules."""

    code: str
    name: str
    is_paid: bool = True
    carries_over: bool = False
    accrual_rate_hours_per_week: Optional[float] = None
    accrual_rate_days_per_year: Optional[float] = None
    max_balance_weeks: Optional[float] = None
    max_balance_days: Optional[float] = None

    @property
    def has_weekly_hourly_accrual(self) -> bool:
        """Whether this leave type accrues on a weekly-hours basis."""
        return self.accrual_rate_hours_per_week is not None

    @property
    def has_daily_annual_accrual(self) -> bool:
        """Whether this leave type accrues on a days-per-year basis."""
        return self.accrual_rate_days_per_year is not None


@dataclass(frozen=True)
class Employee:
    """Employee master data relevant to leave calculations."""

    employee_id: int
    store_id: int
    employment_type: str  # full_time | part_time | casual
    start_date: dt.date
    contracted_hours_per_week: float
    role: str = ""
    job_family: str = ""
    is_high_leave_balance: bool = False
    is_new_starter: bool = False


@dataclass
class LeaveBalance:
    """Running balance for a single employee + leave type combination."""

    employee_id: int
    leave_code: str
    balance_hours: float = 0.0
    accrued_hours: float = 0.0
    taken_hours: float = 0.0
    last_updated: Optional[dt.date] = None
    history: List["LeaveTransaction"] = field(default_factory=list)

    @property
    def balance_days(self) -> float:
        """Balance expressed in 8-hour days (for reporting)."""
        return self.balance_hours / 8.0


@dataclass(frozen=True)
class LeaveTransaction:
    """A single leave accrual or usage event."""

    employee_id: int
    leave_code: str
    transaction_date: dt.date
    transaction_type: str  # ACCRUAL | TAKEN
    hours: float
    balance_after: float
    reason_code: Optional[str] = None


@dataclass
class LeaveExplanation:
    """Human-readable explanation of a leave balance."""

    employee_id: int
    leave_code: str
    current_balance_hours: float
    accrued_hours: float
    taken_hours: float
    explanation_lines: List[str] = field(default_factory=list)

    def to_text(self) -> str:
        """Render the explanation as readable text."""
        lines = [
            f"Leave Balance Explanation — Employee {self.employee_id}",
            f"Leave type: {self.leave_code}",
            f"Current balance: {self.current_balance_hours:.1f} hours "
            f"({self.current_balance_hours / 8.0:.1f} days)",
            f"Total accrued: {self.accrued_hours:.1f} hours",
            f"Total taken: {self.taken_hours:.1f} hours",
            "---",
            *self.explanation_lines,
        ]
        return "\n".join(lines)