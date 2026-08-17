"""Unit tests for NZ Holidays Act rules."""

from __future__ import annotations

import datetime as dt

import pytest

from src.leave_engine.holidays_act import HolidaysActRules


class TestAnnualLeaveEligibility:
    """Tests for annual leave eligibility (12-month vesting)."""

    def test_eligible_after_12_months(self):
        rules = HolidaysActRules()
        start = dt.date(2024, 7, 1)
        as_of = dt.date(2025, 7, 1)
        assert rules.is_eligible_for_annual_leave(start, as_of) is True

    def test_not_eligible_before_12_months(self):
        rules = HolidaysActRules()
        start = dt.date(2024, 7, 1)
        as_of = dt.date(2024, 12, 31)
        assert rules.is_eligible_for_annual_leave(start, as_of) is False

    def test_eligible_exactly_at_12_months(self):
        rules = HolidaysActRules()
        start = dt.date(2024, 7, 1)
        as_of = dt.date(2025, 7, 2)
        assert rules.is_eligible_for_annual_leave(start, as_of) is True

    def test_custom_vesting_period(self):
        rules = HolidaysActRules({"annual_leave": {"vesting_months": 6.0}})
        start = dt.date(2024, 7, 1)
        as_of = dt.date(2025, 1, 1)
        assert rules.is_eligible_for_annual_leave(start, as_of) is True


class TestSickLeaveEligibility:
    """Tests for sick leave eligibility (6-month vesting)."""

    def test_eligible_after_6_months(self):
        rules = HolidaysActRules()
        start = dt.date(2024, 7, 1)
        as_of = dt.date(2025, 1, 1)
        assert rules.is_eligible_for_sick_leave(start, as_of) is True

    def test_not_eligible_before_6_months(self):
        rules = HolidaysActRules()
        start = dt.date(2024, 7, 1)
        as_of = dt.date(2024, 12, 31)
        assert rules.is_eligible_for_sick_leave(start, as_of) is False


class TestAnnualLeaveAccrual:
    """Tests for weekly annual leave accrual calculations."""

    def test_full_time_weekly_accrual(self):
        """4 weeks * 40h / 52 weeks = 3.0769h at 40h contracted."""
        rules = HolidaysActRules()
        accrual = rules.weekly_annual_leave_accrual_hours(40.0)
        assert accrual == pytest.approx(3.0769, abs=0.001)

    def test_part_time_pro_rated(self):
        """20h contracted → half the full-time accrual."""
        rules = HolidaysActRules()
        full_time = rules.weekly_annual_leave_accrual_hours(40.0)
        part_time = rules.weekly_annual_leave_accrual_hours(20.0)
        assert part_time == pytest.approx(full_time / 2, abs=0.001)

    def test_zero_hours(self):
        rules = HolidaysActRules()
        assert rules.weekly_annual_leave_accrual_hours(0.0) == 0.0

    def test_custom_hours_per_week(self):
        rules = HolidaysActRules({"hours_per_week": 30.0})
        # 4 weeks * 30h / 52 = 2.3077h at 30h contracted
        accrual = rules.weekly_annual_leave_accrual_hours(30.0)
        assert accrual == pytest.approx(2.3077, abs=0.001)


class TestSickLeaveAccrual:
    """Tests for weekly sick leave accrual calculations."""

    def test_full_time_weekly_accrual(self):
        """10 days * 8h / 52 weeks = 1.5385h at 40h contracted."""
        rules = HolidaysActRules()
        accrual = rules.weekly_sick_leave_accrual_hours(40.0)
        assert accrual == pytest.approx(1.5385, abs=0.001)

    def test_part_time_pro_rated(self):
        rules = HolidaysActRules()
        full_time = rules.weekly_sick_leave_accrual_hours(40.0)
        part_time = rules.weekly_sick_leave_accrual_hours(16.0)
        assert part_time == pytest.approx(full_time * 0.4, abs=0.001)


class TestBalanceCaps:
    """Tests for balance caps."""

    def test_max_annual_balance(self):
        rules = HolidaysActRules()
        assert rules.max_annual_balance_hours() == pytest.approx(320.0)  # 8 weeks * 40h

    def test_max_annual_balance_custom(self):
        rules = HolidaysActRules({"annual_leave": {"max_balance_weeks": 6.0}})
        assert rules.max_annual_balance_hours() == pytest.approx(240.0)

    def test_max_sick_balance(self):
        rules = HolidaysActRules()
        assert rules.max_sick_balance_hours() == pytest.approx(160.0)  # 20 days * 8h


class TestPayMethods:
    """Tests for pay method selection."""

    def test_full_time_uses_owp(self):
        rules = HolidaysActRules()
        method = rules.pay_method_for("full_time")
        assert method.method == "ordinary_weekly_pay"

    def test_part_time_uses_owp(self):
        rules = HolidaysActRules()
        method = rules.pay_method_for("part_time")
        assert method.method == "ordinary_weekly_pay"

    def test_casual_uses_awe(self):
        rules = HolidaysActRules()
        method = rules.pay_method_for("casual")
        assert method.method == "average_weekly_earnings"


class TestMonthsBetween:
    """Tests for the months_between utility."""

    def test_exact_year(self):
        assert HolidaysActRules.months_between(
            dt.date(2024, 7, 1), dt.date(2025, 7, 1)
        ) == pytest.approx(12.0, abs=0.1)

    def test_six_months(self):
        assert HolidaysActRules.months_between(
            dt.date(2024, 7, 1), dt.date(2025, 1, 1)
        ) == pytest.approx(6.0, abs=0.1)

    def test_less_than_one_month(self):
        assert HolidaysActRules.months_between(
            dt.date(2024, 7, 1), dt.date(2024, 7, 20)
        ) < 1.0