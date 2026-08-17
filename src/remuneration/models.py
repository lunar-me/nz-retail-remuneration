"""Data models for the remuneration costing engine.

Defines dataclasses for remuneration components, employee cost profiles,
and scenario definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RemunerationComponents:
    """The cost components for a single employee's remuneration package."""

    employee_id: int
    base_hourly_rate: float
    contracted_hours_per_week: float
    employment_type: str = "full_time"
    kiwisaver_employer_rate: float = 0.03
    leave_loading_rate: float = 0.08
    insurance_monthly_cost: float = 0.0
    flexibility_premium_rate: float = 0.0

    # --- Derived cost-per-hour components ---
    @property
    def kiwisaver_cost_per_hour(self) -> float:
        """Employer KiwiSaver contribution per hour."""
        return self.base_hourly_rate * self.kiwisaver_employer_rate

    @property
    def leave_loading_cost_per_hour(self) -> float:
        """Leave loading (value of leave in package) per hour."""
        return self.base_hourly_rate * self.leave_loading_rate

    @property
    def insurance_cost_per_hour(self) -> float:
        """Insurance employer cost per hour (assume 160h/month)."""
        return self.insurance_monthly_cost / 160.0

    @property
    def flexibility_cost_per_hour(self) -> float:
        """Flexibility premium per hour."""
        return self.base_hourly_rate * self.flexibility_premium_rate

    @property
    def fully_loaded_cost_per_hour(self) -> float:
        """Total fully-loaded cost per hour."""
        return (
            self.base_hourly_rate
            + self.kiwisaver_cost_per_hour
            + self.leave_loading_cost_per_hour
            + self.insurance_cost_per_hour
            + self.flexibility_cost_per_hour
        )

    @property
    def weekly_cost(self) -> float:
        """Fully-loaded weekly cost based on contracted hours."""
        return self.fully_loaded_cost_per_hour * self.contracted_hours_per_week

    @property
    def annual_cost(self) -> float:
        """Fully-loaded annual cost (52 weeks)."""
        return self.weekly_cost * 52.0


@dataclass
class EmployeeCostProfile:
    """An employee's cost breakdown at current and alternative rates."""

    employee_id: int
    components: RemunerationComponents

    @property
    def base_cost_per_hour(self) -> float:
        return self.components.base_hourly_rate

    @property
    def fully_loaded_cost_per_hour(self) -> float:
        return self.components.fully_loaded_cost_per_hour

    @property
    def annual_cost(self) -> float:
        return self.components.annual_cost


@dataclass(frozen=True)
class CostAssumptions:
    """Configurable cost assumptions for the remuneration model."""

    kiwisaver_employer_rate: float = 0.03
    leave_loading_rate: float = 0.08
    insurance_monthly_employer_cost_mean: float = 45.0
    insurance_monthly_employer_cost_std: float = 15.0
    flexibility_premium_max: float = 0.06
    hours_per_month: float = 160.0
    weeks_per_year: float = 52.0


@dataclass
class Scenario:
    """A remuneration package scenario to model."""

    name: str
    description: str = ""
    # Adjustments (applied on top of current components)
    annual_leave_extra_days: float = 0.0          # +N days annual leave
    sick_leave_extra_days: float = 0.0            # +N days sick leave
    kiwisaver_rate: Optional[float] = None         # override KiwiSaver rate
    leave_loading_rate: Optional[float] = None     # override leave loading
    insurance_adjustment: float = 0.0              # +/- monthly employer cost
    flexibility_premium_max: Optional[float] = None  # override flex premium cap

    def apply_to(self, components: RemunerationComponents) -> RemunerationComponents:
        """Apply this scenario's adjustments to base components."""
        # Adjust flexibility premium if the cap is overridden
        flex_rate = components.flexibility_premium_rate
        if self.flexibility_premium_max is not None:
            # Scale flexibility rate proportionally if the cap changes
            current_cap = 0.06  # default cap from config
            flex_rate = (
                components.flexibility_premium_rate
                / current_cap
                * self.flexibility_premium_max
            )

        # Adjust leave loading for extra leave days
        leave_rate = components.leave_loading_rate
        if self.leave_loading_rate is not None:
            leave_rate = self.leave_loading_rate

        return RemunerationComponents(
            employee_id=components.employee_id,
            base_hourly_rate=components.base_hourly_rate,
            contracted_hours_per_week=components.contracted_hours_per_week,
            employment_type=components.employment_type,
            kiwisaver_employer_rate=(
                self.kiwisaver_rate
                if self.kiwisaver_rate is not None
                else components.kiwisaver_employer_rate
            ),
            leave_loading_rate=leave_rate,
            insurance_monthly_cost=max(
                0.0, components.insurance_monthly_cost + self.insurance_adjustment
            ),
            flexibility_premium_rate=flex_rate,
        )
