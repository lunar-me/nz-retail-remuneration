"""Unit tests for the demand → capacity planner."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from src.capacity import CapacityPlanner, DemandForecaster, RosterSuggester
from src.capacity.labour_standards import LabourStandards


def _make_demand_df() -> pd.DataFrame:
    """Create a small demand DataFrame for testing."""
    return pd.DataFrame(
        [
            {
                "store_id": 1,
                "date": "2026-06-01",
                "day_of_week": 0,
                "is_weekend": False,
                "is_public_holiday": False,
                "is_school_term": True,
                "is_retail_peak": False,
                "demand_index": 100.0,
                "transaction_count": 100,
                "sales_amount": 4500.0,
            },
            {
                "store_id": 1,
                "date": "2026-06-02",
                "day_of_week": 1,
                "is_weekend": False,
                "is_public_holiday": False,
                "is_school_term": True,
                "is_retail_peak": False,
                "demand_index": 150.0,
                "transaction_count": 150,
                "sales_amount": 6750.0,
            },
            {
                "store_id": 1,
                "date": "2026-06-06",
                "day_of_week": 5,
                "is_weekend": True,
                "is_public_holiday": False,
                "is_school_term": True,
                "is_retail_peak": False,
                "demand_index": 200.0,
                "transaction_count": 200,
                "sales_amount": 9000.0,
            },
        ]
    )


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
                "role": "Grocery / Nightfill",
                "job_family": "Grocery",
                "employment_type": "part_time",
                "start_date": "2024-07-01",
                "contracted_hours_per_week": 20.0,
                "base_hourly_rate": 25.0,
                "insurance_enrolled": False,
                "flexibility_preference": 0.4,
                "is_high_leave_balance": False,
                "is_new_starter": False,
                "is_high_flexibility": False,
            },
        ]
    )


def _make_leave_tx_df() -> pd.DataFrame:
    """Create a small leave-transactions DataFrame for testing."""
    return pd.DataFrame(
        [
            {
                "transaction_id": 1,
                "employee_id": 1,
                "leave_code": "ANNUAL",
                "transaction_date": "2026-06-01",
                "transaction_type": "TAKEN",
                "hours": 8.0,
                "balance_after": 100.0,
                "reason_code": "ANNUAL_LEAVE",
            },
            {
                "transaction_id": 2,
                "employee_id": 2,
                "leave_code": "SICK",
                "transaction_date": "2026-06-02",
                "transaction_type": "TAKEN",
                "hours": 4.0,
                "balance_after": 20.0,
                "reason_code": "SICK_LEAVE",
            },
        ]
    )


class TestLabourStandards:
    """Tests for labour standards."""

    def test_productivity_for_role(self):
        ls = LabourStandards()
        assert ls.productivity_for_role("Checkout / Front End") == 28.0
        assert ls.productivity_for_role("Fresh Foods") == 18.0
        assert ls.productivity_for_role("Unknown Role") == 20.0  # default

    def test_required_hours(self):
        ls = LabourStandards()
        # 100 demand / 28 productivity = ~3.57 hours
        hours = ls.required_hours(100.0, "Checkout / Front End")
        assert hours == pytest.approx(3.571, abs=0.01)


class TestDemandForecaster:
    """Tests for the demand forecaster."""

    def test_build_store_profiles(self):
        forecaster = DemandForecaster()
        profiles = forecaster.build_store_profiles(_make_demand_df())
        assert 1 in profiles
        profile = profiles[1]
        assert profile.avg_daily_index == pytest.approx(150.0)
        assert 5 in profile.day_of_week_multipliers  # Saturday

    def test_forecast_day(self):
        forecaster = DemandForecaster()
        profiles = forecaster.build_store_profiles(_make_demand_df())
        forecast = forecaster.forecast_day(profiles[1], dt.date(2026, 6, 1))
        assert forecast > 0

    def test_forecast_period(self):
        forecaster = DemandForecaster()
        profiles = forecaster.build_store_profiles(_make_demand_df())
        df = forecaster.forecast_period(profiles[1], dt.date(2026, 6, 1), dt.date(2026, 6, 7))
        assert len(df) == 7
        assert "forecast_demand_index" in df.columns

    def test_identify_peaks(self):
        forecaster = DemandForecaster()
        demand = _make_demand_df()
        peaks = forecaster.identify_peaks(demand, threshold_multiplier=1.3)
        assert len(peaks) > 0  # Saturday (200) > 1.3 * 150 = 195


class TestCapacityPlanner:
    """Tests for the capacity planner."""

    def test_compute_required_hours(self):
        planner = CapacityPlanner()
        required = planner.compute_required_hours(_make_demand_df())
        assert len(required) > 0
        # 3 demand rows × 7 roles = 21 requirements
        assert len(required) == 21
        assert required[0].store_id == 1
        assert required[0].required_hours > 0

    def test_compute_available_hours(self):
        planner = CapacityPlanner()
        available = planner.compute_available_hours(
            _make_employees_df(),
            _make_leave_tx_df(),
            dt.date(2026, 6, 1),
            dt.date(2026, 6, 7),
        )
        assert len(available) > 0
        # Employee 1: 40/5 = 8h/day, minus 8h on June 1 → 0h that day
        emp1_day1 = [a for a in available if a.employee_id == 1 and a.date == dt.date(2026, 6, 1)]
        assert len(emp1_day1) == 0 or emp1_day1[0].available_hours == 0.0

    def test_compute_capacity_gaps(self):
        planner = CapacityPlanner()
        required = planner.compute_required_hours(_make_demand_df())
        available = planner.compute_available_hours(
            _make_employees_df(),
            _make_leave_tx_df(),
            dt.date(2026, 6, 1),
            dt.date(2026, 6, 7),
        )
        gaps = planner.compute_capacity_gaps(required, available)
        assert len(gaps) == len(required)
        statuses = {g.status for g in gaps}
        assert "UNDER_CAPACITY" in statuses  # 2 employees can't cover all roles

    def test_gaps_to_dataframe(self):
        planner = CapacityPlanner()
        required = planner.compute_required_hours(_make_demand_df())
        available = planner.compute_available_hours(
            _make_employees_df(),
            _make_leave_tx_df(),
            dt.date(2026, 6, 1),
            dt.date(2026, 6, 7),
        )
        gaps = planner.compute_capacity_gaps(required, available)
        df = planner.gaps_to_dataframe(gaps)
        assert "store_id" in df.columns
        assert "status" in df.columns
        assert "gap_hours" in df.columns

    def test_summarize_gaps(self):
        planner = CapacityPlanner()
        required = planner.compute_required_hours(_make_demand_df())
        available = planner.compute_available_hours(
            _make_employees_df(),
            _make_leave_tx_df(),
            dt.date(2026, 6, 1),
            dt.date(2026, 6, 7),
        )
        gaps = planner.compute_capacity_gaps(required, available)
        df = planner.gaps_to_dataframe(gaps)
        summary = planner.summarize_gaps(df, ["store_id"])
        assert len(summary) == 1
        assert "under_capacity_days" in summary.columns
        assert "total_gap" in summary.columns


class TestRosterSuggester:
    """Tests for the roster suggester."""

    def test_suggest_generates_suggestions(self):
        planner = CapacityPlanner()
        required = planner.compute_required_hours(_make_demand_df())
        available = planner.compute_available_hours(
            _make_employees_df(),
            _make_leave_tx_df(),
            dt.date(2026, 6, 1),
            dt.date(2026, 6, 7),
        )
        gaps = planner.compute_capacity_gaps(required, available)

        suggester = RosterSuggester()
        suggestions = suggester.suggest(gaps, available)
        assert len(suggestions) > 0
        assert all(s.suggestion_type in ("ADD_SHIFT", "REDUCE_HOURS") for s in suggestions)

    def test_suggestions_to_dataframe(self):
        suggester = RosterSuggester()
        from src.capacity.models import RosterSuggestion

        suggestions = [
            RosterSuggestion(
                store_id=1,
                date=dt.date(2026, 6, 1),
                role="Checkout / Front End",
                gap_hours=5.0,
                suggestion_type="ADD_SHIFT",
            )
        ]
        df = suggester.suggestions_to_dataframe(suggestions)
        assert "store_id" in df.columns
        assert "rationale" in df.columns