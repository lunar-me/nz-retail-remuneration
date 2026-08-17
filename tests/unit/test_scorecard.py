"""Unit tests for the integrated scorecard."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from src.scorecard import AlertEngine, MetricCalculator, ScorecardBuilder
from src.scorecard.models import ProgrammeMetric, StoreMetric


def _make_employees_df() -> pd.DataFrame:
    """Create a small employees DataFrame."""
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
                "flexibility_preference": 0.4,
                "is_high_leave_balance": False,
                "is_new_starter": False,
                "is_high_flexibility": False,
            },
            {
                "employee_id": 3,
                "store_id": 1,
                "role": "Grocery / Nightfill",
                "job_family": "Grocery",
                "employment_type": "casual",
                "start_date": "2024-07-01",
                "contracted_hours_per_week": 15.0,
                "base_hourly_rate": 27.0,
                "insurance_enrolled": False,
                "flexibility_preference": 0.5,
                "is_high_leave_balance": False,
                "is_new_starter": False,
                "is_high_flexibility": False,
            },
        ]
    )


def _make_stores_df() -> pd.DataFrame:
    """Create a small stores DataFrame."""
    return pd.DataFrame(
        [
            {
                "store_id": 1,
                "store_name": "Store 01",
                "region": "Auckland",
                "format": "Supermarket",
                "size_band": "Large",
                "trading_pattern": "standard",
                "weekday_open": "07:00",
                "weekday_close": "21:00",
                "saturday_open": "07:00",
                "saturday_close": "21:00",
                "sunday_open": "08:00",
                "sunday_close": "20:00",
                "is_tight_capacity": True,
            }
        ]
    )


def _make_leave_types_df() -> pd.DataFrame:
    """Create a small leave-types DataFrame."""
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
            }
        ]
    )


def _make_remuneration_df() -> pd.DataFrame:
    """Create a small remuneration DataFrame."""
    return pd.DataFrame(
        [
            {
                "employee_id": 1,
                "base_hourly_rate": 26.0,
                "kiwisaver_employer_rate": 0.03,
                "kiwisaver_employer_cost_per_hour": 0.78,
                "leave_loading_rate": 0.08,
                "leave_loading_cost_per_hour": 2.08,
                "insurance_monthly_cost": 45.0,
                "insurance_cost_per_hour": 0.28,
                "flexibility_premium_rate": 0.04,
                "flexibility_premium_cost_per_hour": 1.04,
                "fully_loaded_cost_per_hour": 30.18,
            },
            {
                "employee_id": 2,
                "base_hourly_rate": 25.0,
                "kiwisaver_employer_rate": 0.03,
                "kiwisaver_employer_cost_per_hour": 0.75,
                "leave_loading_rate": 0.08,
                "leave_loading_cost_per_hour": 2.00,
                "insurance_monthly_cost": 0.0,
                "insurance_cost_per_hour": 0.0,
                "flexibility_premium_rate": 0.02,
                "flexibility_premium_cost_per_hour": 0.50,
                "fully_loaded_cost_per_hour": 28.25,
            },
            {
                "employee_id": 3,
                "base_hourly_rate": 27.0,
                "kiwisaver_employer_rate": 0.03,
                "kiwisaver_employer_cost_per_hour": 0.81,
                "leave_loading_rate": 0.08,
                "leave_loading_cost_per_hour": 2.16,
                "insurance_monthly_cost": 0.0,
                "insurance_cost_per_hour": 0.0,
                "flexibility_premium_rate": 0.03,
                "flexibility_premium_cost_per_hour": 0.81,
                "fully_loaded_cost_per_hour": 30.78,
            },
        ]
    )


def _make_empty_demand_df() -> pd.DataFrame:
    """Create an empty demand DataFrame."""
    return pd.DataFrame(columns=[
        "store_id", "date", "day_of_week", "is_weekend",
        "is_public_holiday", "is_school_term", "is_retail_peak",
        "demand_index", "transaction_count", "sales_amount",
    ])


def _make_empty_rosters_df() -> pd.DataFrame:
    """Create an empty rosters DataFrame."""
    return pd.DataFrame(columns=[
        "roster_id", "employee_id", "store_id", "work_date",
        "shift_start", "shift_end", "hours_worked", "role_on_day",
        "is_weekend", "is_public_holiday", "penalty_flag",
    ])


def _make_empty_leave_tx_df() -> pd.DataFrame:
    """Create an empty leave-transactions DataFrame."""
    return pd.DataFrame(columns=[
        "transaction_id", "employee_id", "leave_code", "transaction_date",
        "transaction_type", "hours", "balance_after", "reason_code",
    ])


class TestMetricCalculator:
    """Tests for the metric calculator."""

    def test_programme_metrics(self):
        calc = MetricCalculator()
        metrics = calc.programme_metrics(
            _make_employees_df(),
            _make_leave_types_df(),
            _make_empty_leave_tx_df(),
            _make_remuneration_df(),
            as_of=dt.date(2026, 6, 30),
        )
        names = {m.metric_name for m in metrics}
        assert "avg_annual_leave_balance_days" in names
        assert "insurance_takeup_rate" in names
        assert "avg_flexibility_preference" in names
        assert "total_annual_cost" in names
        assert "headcount" in names

    def test_store_metrics(self):
        calc = MetricCalculator()
        metrics = calc.store_metrics(
            _make_employees_df(),
            _make_stores_df(),
            _make_leave_types_df(),
            _make_empty_leave_tx_df(),
            _make_empty_demand_df(),
            _make_empty_rosters_df(),
            as_of=dt.date(2026, 6, 30),
        )
        assert len(metrics) > 0
        assert all(m.store_id == 1 for m in metrics)
        names = {m.metric_name for m in metrics}
        assert "headcount" in names
        assert "insurance_takeup" in names
        assert "tight_capacity_store" in names


class TestAlertEngine:
    """Tests for the alert engine."""

    def test_programme_alerts(self):
        engine = AlertEngine()
        metrics = [
            ProgrammeMetric(
                metric_name="avg_annual_leave_balance_days",
                metric_value=60.0,
                metric_unit="days",
                status="CRITICAL",
            ),
            ProgrammeMetric(
                metric_name="insurance_takeup_rate",
                metric_value=0.35,
                metric_unit="pct",
                status="WARNING",
            ),
            ProgrammeMetric(
                metric_name="avg_flexibility_preference",
                metric_value=0.6,
                metric_unit="score",
                status="OK",
            ),
        ]
        alerts = engine.programme_alerts(metrics)
        assert len(alerts) == 2
        assert any(a.alert_type == "leave_liability" for a in alerts)
        assert any(a.alert_type == "insurance_takeup" for a in alerts)

    def test_store_alerts(self):
        engine = AlertEngine()
        metrics = [
            StoreMetric(
                store_id=1,
                metric_name="capacity_ratio",
                metric_value=0.7,
                metric_unit="ratio",
                status="CRITICAL",
                notes="2 under-capacity days",
            ),
            StoreMetric(
                store_id=1,
                metric_name="insurance_takeup",
                metric_value=0.5,
                metric_unit="pct",
                status="OK",
            ),
        ]
        alerts = engine.store_alerts(metrics)
        assert len(alerts) == 1
        assert alerts[0].alert_type == "capacity"
        assert alerts[0].store_id == 1

    def test_alerts_to_dataframe(self):
        engine = AlertEngine()
        metrics = [
            ProgrammeMetric(
                metric_name="avg_annual_leave_balance_days",
                metric_value=60.0,
                metric_unit="days",
                status="CRITICAL",
            )
        ]
        alerts = engine.programme_alerts(metrics)
        df = engine.alerts_to_dataframe(alerts)
        assert "alert_type" in df.columns
        assert "severity" in df.columns


class TestScorecardBuilder:
    """Tests for the scorecard builder."""

    def test_build(self):
        builder = ScorecardBuilder()
        scorecard = builder.build(
            _make_employees_df(),
            _make_stores_df(),
            _make_leave_types_df(),
            _make_empty_leave_tx_df(),
            _make_remuneration_df(),
            _make_empty_demand_df(),
            _make_empty_rosters_df(),
            as_of=dt.date(2026, 6, 30),
        )
        assert len(scorecard.metrics) > 0
        assert len(scorecard.store_scorecards) == 1
        assert scorecard.overall_health in ("OK", "WARNING", "CRITICAL")

    def test_render_text(self):
        builder = ScorecardBuilder()
        scorecard = builder.build(
            _make_employees_df(),
            _make_stores_df(),
            _make_leave_types_df(),
            _make_empty_leave_tx_df(),
            _make_remuneration_df(),
            _make_empty_demand_df(),
            _make_empty_rosters_df(),
            as_of=dt.date(2026, 6, 30),
        )
        text = builder.render_text(scorecard)
        assert "SCORECARD" in text
        assert "Programme Metrics" in text