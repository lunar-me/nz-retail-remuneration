"""NZ Holidays Act 2003-oriented rules (simplified but explicit).

This module encodes the key compliance concepts from the Holidays Act 2003
that are relevant to leave accrual and entitlement calculations:

- Annual leave: 4 weeks per year after 12 months continuous employment
- Sick leave: 10 days per year (statutory minimum)
- Bereavement leave: 3 days per year
- Ordinary weekly pay / average weekly earnings flags (simplified)
- Pro-rata treatment for part-time / casual / variable-hours employees

The rules here are deliberately simplified to be transparent and auditable.
They are not legal advice and should be reviewed by an employment lawyer
before production use.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PayCalculationMethod:
    """Encapsulates the OWP/AWE method choice (simplified)."""

    method: str  # "ordinary_weekly_pay" | "average_weekly_earnings" | "relevant_daily_pay"
    description: str = ""


# Simplified OWP/AWE flags from config
DEFAULT_PAY_METHODS: Dict[str, PayCalculationMethod] = {
    "ordinary_weekly_pay": PayCalculationMethod(
        method="ordinary_weekly_pay",
        description=(
            "Ordinary Weekly Pay: based on the employee's usual weekly "
            "earnings at the time leave is taken, including regular "
            "allowances and the cash value of board/lodging if applicable."
        ),
    ),
    "average_weekly_earnings": PayCalculationMethod(
        method="average_weekly_earnings",
        description=(
            "Average Weekly Earnings: average of gross earnings over the "
            "52 weeks immediately before the end of the pay period."
        ),
    ),
    "relevant_daily_pay": PayCalculationMethod(
        method="relevant_daily_pay",
        description=(
            "Relevant Daily Pay: what the employee would have been paid "
            "for the day if they had worked (used for public holidays)."
        ),
    ),
}


class HolidaysActRules:
    """Encapsulates NZ Holidays Act-oriented calculation rules.

    The rules are configurable via a dict (typically loaded from
    ``configs/leave_rules.yaml``) so assumptions live in one place.
    """

    # Statutory defaults (Holidays Act 2003)
    DEFAULT_ANNUAL_LEAVE_WEEKS = 4.0
    DEFAULT_SICK_LEAVE_DAYS = 10.0
    DEFAULT_BEREAVEMENT_DAYS = 3.0
    DEFAULT_HOURS_PER_DAY = 8.0
    DEFAULT_HOURS_PER_WEEK = 40.0

    def __init__(self, rules: Optional[Dict] = None):
        """Initialise the rules wrapper.

        Parameters
        ----------
        rules : Optional[Dict]
            Rules dict, typically from ``configs/leave_rules.yaml``.
            If ``None``, statutory defaults are used.
        """
        self._rules = rules or {}

        self.annual_leave_weeks = float(
            self._rules.get("annual_leave", {}).get(
                "weeks_per_year", self.DEFAULT_ANNUAL_LEAVE_WEEKS
            )
        )
        self.sick_leave_days = float(
            self._rules.get("sick_leave", {}).get(
                "days_per_year", self.DEFAULT_SICK_LEAVE_DAYS
            )
        )
        self.bereavement_days = float(
            self._rules.get("bereavement_leave", {}).get(
                "days_per_year", self.DEFAULT_BEREAVEMENT_DAYS
            )
        )
        self.hours_per_day = float(
            self._rules.get("hours_per_day", self.DEFAULT_HOURS_PER_DAY)
        )
        self.hours_per_week = float(
            self._rules.get("hours_per_week", self.DEFAULT_HOURS_PER_WEEK)
        )

        # Eligibility: months of continuous service before annual leave vests
        self.annual_leave_vesting_months = float(
            self._rules.get("annual_leave", {}).get(
                "vesting_months", 12.0
            )
        )

        # Pay calculation method flag
        self.ordinary_weekly_pay_method = self._rules.get(
            "ordinary_weekly_pay_method", "average_of_last_4_weeks"
        )

    # ------------------------------------------------------------------
    # Eligibility
    # ------------------------------------------------------------------
    def is_eligible_for_annual_leave(self, start_date: dt.date, as_of: dt.date) -> bool:
        """Check whether an employee is eligible for annual leave.

        Under the Holidays Act, annual leave vests after 12 months of
        continuous employment.
        """
        months_employed = self.months_between(start_date, as_of)
        return months_employed >= self.annual_leave_vesting_months

    def is_eligible_for_sick_leave(self, start_date: dt.date, as_of: dt.date) -> bool:
        """Check whether an employee is eligible for sick leave.

        Under the Holidays Act, sick leave is available after 6 months of
        continuous employment (simplified — statutory requirement is after
        6 months for the current entitlement).
        """
        months_employed = self.months_between(start_date, as_of)
        return months_employed >= 6.0

    def is_eligible_for_bereavement(self, start_date: dt.date, as_of: dt.date) -> bool:
        """Check whether an employee is eligible for bereavement leave.

        Available after 6 months of continuous employment (simplified).
        """
        months_employed = self.months_between(start_date, as_of)
        return months_employed >= 6.0

    # ------------------------------------------------------------------
    # Accrual calculations
    # ------------------------------------------------------------------
    def weekly_annual_leave_accrual_hours(
        self,
        contracted_hours_per_week: float,
    ) -> float:
        """Return the weekly annual-leave accrual in hours.

        Calculated as: (annual_leave_weeks * hours_per_week) / 52 weeks,
        pro-rated by the employee's contracted hours.

        Example: 4 weeks * 40h = 160h/year = 3.0769h/week at 40h contracted.
        """
        annual_hours = self.annual_leave_weeks * self.hours_per_week
        weekly = annual_hours / 52.0
        pro_ratio = contracted_hours_per_week / self.hours_per_week
        return weekly * pro_ratio

    def weekly_sick_leave_accrual_hours(
        self,
        contracted_hours_per_week: float,
    ) -> float:
        """Return the weekly sick-leave accrual in hours.

        Calculated as: (sick_leave_days * hours_per_day) / 52 weeks,
        pro-rated by the employee's contracted hours.
        """
        annual_hours = self.sick_leave_days * self.hours_per_day
        weekly = annual_hours / 52.0
        pro_ratio = contracted_hours_per_week / self.hours_per_week
        return weekly * pro_ratio

    def weekly_bereavement_accrual_hours(
        self,
        contracted_hours_per_week: float,
    ) -> float:
        """Return the weekly bereavement accrual in hours.

        Calculated as: (bereavement_days * hours_per_day) / 52 weeks,
        pro-rated by the employee's contracted hours.
        """
        annual_hours = self.bereavement_days * self.hours_per_day
        weekly = annual_hours / 52.0
        pro_ratio = contracted_hours_per_week / self.hours_per_week
        return weekly * pro_ratio

    def max_annual_balance_hours(self) -> float:
        """Return the maximum annual leave balance in hours.

        Uses the statutory cap of 8 weeks (configurable via leave_rules).
        """
        max_weeks = float(
            self._rules.get("annual_leave", {}).get("max_balance_weeks", 8.0)
        )
        return max_weeks * self.hours_per_week

    def max_sick_balance_hours(self) -> float:
        """Return the maximum sick leave balance in hours.

        Statutory cap of 20 days (configurable).
        """
        max_days = float(
            self._rules.get("sick_leave", {}).get("max_balance_days", 20.0)
        )
        return max_days * self.hours_per_day

    # ------------------------------------------------------------------
    # Pay calculation helpers (simplified flags)
    # ------------------------------------------------------------------
    def pay_method_for(self, employment_type: str) -> PayCalculationMethod:
        """Return the pay calculation method for an employment type.

        Simplified: full-time/part-time use OWP; casual/variable uses AWE.
        """
        if employment_type == "casual":
            return DEFAULT_PAY_METHODS["average_weekly_earnings"]
        return DEFAULT_PAY_METHODS["ordinary_weekly_pay"]

    def pay_method_description(self, employment_type: str) -> str:
        """Return the human-readable description of the pay method."""
        return self.pay_method_for(employment_type).description

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    @staticmethod
    def months_between(start: dt.date, end: dt.date) -> float:
        """Return the number of (fractional) months between two dates."""
        months = (end.year - start.year) * 12 + (end.month - start.month)
        # Add fractional month for day difference
        days_in_end_month = 30.44  # average
        day_fraction = (end.day - start.day) / days_in_end_month
        return months + day_fraction