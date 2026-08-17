"""Unit tests for the leave accrual engine."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from src.leave_engine.accrual import LeaveAccrualEngine
from src.leave_engine.models import LeaveType


def _make_employees_df() -> pd.DataFrame:
    """Create a small employees DataFrame for testing."""
    return pd.DataFrame(
        [
            {
                "employee_id": 1,
                "store_id": 1,
                "role": "Checkout / Front End",
                "job_family": "Checkout",
                "employment_type": "full_time",
                "start_date": "2024-07-01",
                "contracted_hours_per_week": 40.0,
                "base_hourly_rate": 26.0,
                "insurance_enrolled": True,
                "flexibility_preference": 0.6,
                "is_high_leave_balance": False,
                "is_new_starter": False,
                "is_high_flexibility": False,
            },
            {
                "employee_id": 2,
                "store_id": 1,
                "role": "Checkout / Front End",
                "job_family": "Checkout",
                "employment_type": "part_time",
                "start_date": "2024-07-01",
                "contracted_hours_per_week": 20.0,
                "base_hourly_rate": 25.0,
                "insurance_enrolled": False,
                "flexibility_preference": 0.5,
                "is_high_leave_balance": False,
                "is_new_starter": False,
                "is_high_flexibility": False,
            },
        ]
    )


def _make_leave_types_df() -> pd.DataFrame:
    """Create a small leave-types DataFrame for testing."""
    return pd.DataFrame(
        [
            {
                "leave_code": "ANNUAL",
                "leave_name": "Annual Leave",
                "is_paid": True,
                "carries_over": True,
                "accrual_rate_hours_per_week": 3.0769,
                "accrual_rate_days_per_year": None,
                "max_balance_weeks": 8.0,
                "max_balance_days": None,
            },
            {
                "leave_code": "SICK",
                "leave_name": "Sick Leave",
                "is_paid": True,
                "carries_over": True,
                "accrual_rate_hours_per_week": None,
                "accrual_rate_days_per_year": 10.0,
                "max_balance_weeks": None,
                "max_balance_days": 20.0,
            },
            {
                "leave_code": "BEREAVEMENT",
                "leave_name": "Bereavement Leave",
                "is_paid": True,
                "carries_over": False,
                "accrual_rate_hours_per_week": None,
                "accrual_rate_days_per_year": 3.0,
                "max_balance_weeks": None,
                "max_balance_days": None,
            },
        ]
    )


def _make_leave_tx_df() -> pd.DataFrame:
    """Create a small leave-transactions DataFrame for testing.

    Employee 1: 2 weeks of annual accrual + 1 day taken
    Employee 2: 1 week of annual accrual
    """
    return pd.DataFrame(
        [
            {
                "transaction_id": 1,
                "employee_id": 1,
                "leave_code": "ANNUAL",
                "transaction_date": "2024-07-01",
                "transaction_type": "ACCRUAL",
                "hours": 3.0769,
                "balance_after": 3.0769,
                "reason_code": None,
            },
            {
                "transaction_id": 2,
                "employee_id": 1,
                "leave_code": "ANNUAL",
                "transaction_date": "2024-07-08",
                "transaction_type": "ACCRUAL",
                "hours": 3.0769,
                "balance_after": 6.1538,
                "reason_code": None,
            },
            {
                "transaction_id": 3,
                "employee_id": 1,
                "leave_code": "ANNUAL",
                "transaction_date": "2024-07-15",
                "transaction_type": "TAKEN",
                "hours": 8.0,
                "balance_after": -1.8462,
                "reason_code": "ANNUAL_LEAVE",
            },
            {
                "transaction_id": 4,
                "employee_id": 2,
                "leave_code": "ANNUAL",
                "transaction_date": "2024-07-01",
                "transaction_type": "ACCRUAL",
                "hours": 1.5385,
                "balance_after": 1.5385,
                "reason_code": None,
            },
        ]
    )


class TestLeaveAccrualEngine:
    """Tests for the leave accrual engine."""

    def test_load_leave_types(self):
        engine = LeaveAccrualEngine(as_of=dt.date(2025, 1, 1))
        types = engine.load_leave_types(_make_leave_types_df())
        assert "ANNUAL" in types
        assert isinstance(types["ANNUAL"], LeaveType)
        assert types["ANNUAL"].accrual_rate_hours_per_week == pytest.approx(3.0769)

    def test_load_employees(self):
        engine = LeaveAccrualEngine(as_of=dt.date(2025, 1, 1))
        employees = engine.load_employees(_make_employees_df())
        assert 1 in employees
        assert employees[1].employment_type == "full_time"
        assert employees[1].contracted_hours_per_week == 40.0

    def test_calculate_balances_full_time(self):
        engine = LeaveAccrualEngine(as_of=dt.date(2025, 1, 1))
        balances = engine.calculate_balances(
            _make_employees_df(),
            _make_leave_types_df(),
            _make_leave_tx_df(),
            employee_ids=[1],
        )
        assert 1 in balances
        assert "ANNUAL" in balances[1]
        annual = balances[1]["ANNUAL"]
        # 2 weeks accrual (6.1538h) - 1 day taken (8h) = -1.8462h
        # plus fill_missing_accrual adds weeks from 2024-07-01 to as_of
        assert annual.accrued_hours > 0
        assert annual.taken_hours == 8.0

    def test_calculate_balances_part_time(self):
        engine = LeaveAccrualEngine(as_of=dt.date(2025, 1, 1))
        balances = engine.calculate_balances(
            _make_employees_df(),
            _make_leave_types_df(),
            _make_leave_tx_df(),
            employee_ids=[2],
        )
        assert 2 in balances
        assert "ANNUAL" in balances[2]
        annual = balances[2]["ANNUAL"]
        # Part-time: 1 week accrual = 1.5385h + fill_missing from start
        assert annual.accrued_hours >= 1.5385

    def test_new_starter_not_eligible(self):
        """A new starter (< 12 months) should not get annual leave accrual."""
        emp_df = _make_employees_df()
        emp_df.loc[0, "start_date"] = "2025-12-01"  # < 12 months from as_of
        emp_df.loc[0, "is_new_starter"] = True

        engine = LeaveAccrualEngine(as_of=dt.date(2026, 6, 30))
        balances = engine.calculate_balances(
            emp_df,
            _make_leave_types_df(),
            pd.DataFrame(),  # no transactions
            employee_ids=[1],
        )
        # New starter, not yet eligible → no annual leave
        assert 1 in balances
        assert "ANNUAL" in balances[1]
        assert balances[1]["ANNUAL"].accrued_hours == 0.0

    def test_high_leave_balance_employee(self):
        """A long-tenure employee should accumulate a large balance."""
        emp_df = _make_employees_df()
        emp_df.loc[0, "is_high_leave_balance"] = True
        emp_df.loc[0, "start_date"] = "2010-01-01"

        engine = LeaveAccrualEngine(as_of=dt.date(2026, 6, 30))
        balances = engine.calculate_balances(
            emp_df,
            _make_leave_types_df(),
            pd.DataFrame(),  # no transactions - fill from start
            employee_ids=[1],
        )
        annual = balances[1]["ANNUAL"]
        # Long tenure, no usage → should hit the max balance cap
        assert annual.accrued_hours > 0
        # 8 weeks * 40h = 320h cap
        assert annual.balance_hours <= 320.0


class TestLeaveBalanceSummary:
    """Tests for the balance calculator summary."""

    def test_summary_has_expected_columns(self):
        from src.leave_engine.balance import LeaveBalanceCalculator

        calc = LeaveBalanceCalculator(as_of=dt.date(2025, 1, 1))
        summary = calc.current_balances_summary(
            _make_employees_df(),
            _make_leave_types_df(),
            _make_leave_tx_df(),
        )
        expected_cols = {
            "employee_id",
            "store_id",
            "employment_type",
            "role",
            "leave_code",
            "balance_hours",
            "balance_days",
            "accrued_hours",
            "taken_hours",
            "last_updated",
        }
        assert expected_cols.issubset(summary.columns)

    def test_projections(self):
        from src.leave_engine.balance import LeaveBalanceCalculator

        calc = LeaveBalanceCalculator(as_of=dt.date(2025, 1, 1))
        projections = calc.project_all_balances(
            _make_employees_df(),
            _make_leave_types_df(),
            _make_leave_tx_df(),
            weeks_ahead=52.0,
        )
        assert len(projections) > 0
        assert "projected_hours" in projections.columns
        assert all(projections["projected_hours"] >= 0)