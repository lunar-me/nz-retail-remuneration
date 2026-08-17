"""Unit tests for the remuneration costing engine."""

from __future__ import annotations

import pandas as pd
import pytest

from src.remuneration.costing import RemunerationCostingEngine
from src.remuneration.models import (
    CostAssumptions,
    RemunerationComponents,
    Scenario,
)
from src.remuneration.scenarios import ScenarioEngine


def _make_remuneration_df() -> pd.DataFrame:
    """Create a small remuneration_components DataFrame for testing."""
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
                "insurance_cost_per_hour": 0.28125,
                "flexibility_premium_rate": 0.04,
                "flexibility_premium_cost_per_hour": 1.04,
                "fully_loaded_cost_per_hour": 30.18125,
            },
            {
                "employee_id": 2,
                "base_hourly_rate": 28.0,
                "kiwisaver_employer_rate": 0.03,
                "kiwisaver_employer_cost_per_hour": 0.84,
                "leave_loading_rate": 0.08,
                "leave_loading_cost_per_hour": 2.24,
                "insurance_monthly_cost": 0.0,
                "insurance_cost_per_hour": 0.0,
                "flexibility_premium_rate": 0.02,
                "flexibility_premium_cost_per_hour": 0.56,
                "fully_loaded_cost_per_hour": 31.64,
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
                "role": "Checkout / Front End",
                "job_family": "Checkout",
                "employment_type": "part_time",
                "start_date": "2024-07-01",
                "contracted_hours_per_week": 20.0,
                "base_hourly_rate": 28.0,
                "insurance_enrolled": False,
                "flexibility_preference": 0.4,
                "is_high_leave_balance": False,
                "is_new_starter": False,
                "is_high_flexibility": False,
            },
        ]
    )


class TestRemunerationComponents:
    """Tests for the RemunerationComponents derived calculations."""

    def test_kiwisaver_cost_per_hour(self):
        comp = RemunerationComponents(
            employee_id=1, base_hourly_rate=26.0, contracted_hours_per_week=40.0,
            kiwisaver_employer_rate=0.03,
        )
        assert comp.kiwisaver_cost_per_hour == pytest.approx(0.78, abs=0.001)

    def test_leave_loading_cost_per_hour(self):
        comp = RemunerationComponents(
            employee_id=1, base_hourly_rate=26.0, contracted_hours_per_week=40.0,
            leave_loading_rate=0.08,
        )
        assert comp.leave_loading_cost_per_hour == pytest.approx(2.08, abs=0.001)

    def test_insurance_cost_per_hour(self):
        comp = RemunerationComponents(
            employee_id=1, base_hourly_rate=26.0, contracted_hours_per_week=40.0,
            insurance_monthly_cost=45.0,
        )
        assert comp.insurance_cost_per_hour == pytest.approx(0.28125, abs=0.001)

    def test_flexibility_cost_per_hour(self):
        comp = RemunerationComponents(
            employee_id=1, base_hourly_rate=26.0, contracted_hours_per_week=40.0,
            flexibility_premium_rate=0.04,
        )
        assert comp.flexibility_cost_per_hour == pytest.approx(1.04, abs=0.001)

    def test_fully_loaded_cost_per_hour(self):
        comp = RemunerationComponents(
            employee_id=1,
            base_hourly_rate=26.0,
            contracted_hours_per_week=40.0,
            kiwisaver_employer_rate=0.03,
            leave_loading_rate=0.08,
            insurance_monthly_cost=45.0,
            flexibility_premium_rate=0.04,
        )
        # 26 + 0.78 + 2.08 + 0.28125 + 1.04 = 30.18125
        assert comp.fully_loaded_cost_per_hour == pytest.approx(30.18125, abs=0.01)

    def test_annual_cost(self):
        comp = RemunerationComponents(
            employee_id=1,
            base_hourly_rate=26.0,
            contracted_hours_per_week=40.0,
            kiwisaver_employer_rate=0.03,
            leave_loading_rate=0.08,
            insurance_monthly_cost=45.0,
            flexibility_premium_rate=0.04,
        )
        # 30.18125 * 40 * 52 = $62,777
        assert comp.annual_cost == pytest.approx(62777.0, abs=100.0)


class TestRemunerationCostingEngine:
    """Tests for the costing engine."""

    def test_load_components(self):
        engine = RemunerationCostingEngine()
        components = engine.load_components(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        assert 1 in components
        assert 2 in components
        assert components[1].base_hourly_rate == 26.0
        assert components[1].contracted_hours_per_week == 40.0

    def test_cost_summary(self):
        engine = RemunerationCostingEngine()
        summary = engine.cost_summary(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        assert len(summary) == 2
        assert "fully_loaded_cost_per_hour" in summary.columns
        assert "annual_cost" in summary.columns
        assert summary["annual_cost"].sum() > 0

    def test_total_annual_cost(self):
        engine = RemunerationCostingEngine()
        summary = engine.cost_summary(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        total = engine.total_annual_cost(summary)
        assert total > 0

    def test_cost_breakdown(self):
        engine = RemunerationCostingEngine()
        summary = engine.cost_summary(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        breakdown = engine.cost_breakdown(summary)
        assert "base_pay" in breakdown
        assert "kiwisaver" in breakdown
        assert "leave_loading" in breakdown
        assert "insurance" in breakdown
        assert "flexibility" in breakdown
        assert "total" in breakdown
        # Components should sum approximately to total
        component_sum = sum(v for k, v in breakdown.items() if k != "total")
        assert component_sum == pytest.approx(breakdown["total"], rel=0.05)

    def test_aggregate_by_employment_type(self):
        engine = RemunerationCostingEngine()
        summary = engine.cost_summary(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        agg = engine.aggregate_by(summary, ["employment_type"])
        assert len(agg) == 2
        assert "headcount" in agg.columns
        assert "total_annual_cost" in agg.columns
        assert agg["headcount"].sum() == 2


class TestScenarioEngine:
    """Tests for the scenario engine."""

    def test_baseline_scenario_no_change(self):
        engine = RemunerationCostingEngine()
        components = engine.load_components(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        summary = engine.cost_summary(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        base = engine.total_annual_cost(summary)

        scenario = Scenario(name="Baseline")
        scenario_engine = ScenarioEngine(engine)
        result = scenario_engine.run_scenario(scenario, components, base)

        assert result.annual_cost_impact == pytest.approx(0.0, abs=0.01)

    def test_higher_kiwisaver_increases_cost(self):
        engine = RemunerationCostingEngine()
        components = engine.load_components(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        summary = engine.cost_summary(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        base = engine.total_annual_cost(summary)

        scenario = Scenario(
            name="Higher KiwiSaver",
            kiwisaver_rate=0.04,
        )
        scenario_engine = ScenarioEngine(engine)
        result = scenario_engine.run_scenario(scenario, components, base)

        assert result.annual_cost_impact > 0

    def test_higher_insurance_increases_cost(self):
        engine = RemunerationCostingEngine()
        components = engine.load_components(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        summary = engine.cost_summary(
            _make_remuneration_df(),
            _make_employees_df(),
        )
        base = engine.total_annual_cost(summary)

        scenario = Scenario(
            name="Higher Insurance",
            insurance_adjustment=20.0,
        )
        scenario_engine = ScenarioEngine(engine)
        result = scenario_engine.run_scenario(scenario, components, base)

        assert result.annual_cost_impact > 0

    def test_scenarios_to_dataframe(self):
        scenario_engine = ScenarioEngine()
        results = [
            scenario_engine.run_scenario(
                Scenario(name="A"), {}, 1000.0
            )
        ]
        # Fix: empty components means no cost
        df = scenario_engine.scenarios_to_dataframe(results)
        assert "scenario" in df.columns
        assert "annual_cost_impact" in df.columns

    def test_default_scenarios(self):
        scenarios = ScenarioEngine.default_scenarios()
        assert len(scenarios) >= 6
        assert any(s.name == "Baseline" for s in scenarios)
        assert any("Annual Leave" in s.name for s in scenarios)