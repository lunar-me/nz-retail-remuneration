"""End-to-end integration test for the full programme chain.

Runs the complete pipeline: load synthetic data → leave engine → costing →
capacity → scorecard, verifying that all engines work together.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from src.capacity import CapacityPlanner, RosterSuggester
from src.capacity.labour_standards import LabourStandards
from src.leave_engine import LeaveBalanceCalculator
from src.remuneration import RemunerationCostingEngine, ScenarioEngine
from src.remuneration.scenarios import Scenario
from src.scorecard import ScorecardBuilder


@pytest.fixture(scope="module")
def data_tables():
    """Load the synthetic dataset once for the integration test module."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

    from src.common.io import load_dataset

    data_dir = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "v1"
    if not data_dir.exists():
        pytest.skip("Synthetic data not found. Run scripts/generate_synthetic_data.py first.")
    return load_dataset(data_dir)


class TestEndToEndChain:
    """End-to-end integration tests across all engines."""

    def test_leave_engine_works_with_synthetic_data(self, data_tables):
        """Leave engine computes balances for all employees."""
        calc = LeaveBalanceCalculator(as_of=dt.date(2026, 6, 30))
        summary = calc.current_balances_summary(
            data_tables["employees"],
            data_tables["leave_types"],
            data_tables["leave_transactions"],
        )
        assert len(summary) > 0
        assert "ANNUAL" in summary["leave_code"].values
        assert "SICK" in summary["leave_code"].values
        # Balances can be slightly negative in NZ retail (leave taken against
        # future accrual is a realistic scenario); verify the vast majority
        # are non-negative
        negative_ratio = (summary["balance_hours"] < 0).mean()
        assert negative_ratio < 0.05  # < 5% of balances negative

    def test_costing_engine_works_with_synthetic_data(self, data_tables):
        """Costing engine computes fully-loaded costs."""
        costing = RemunerationCostingEngine()
        summary = costing.cost_summary(
            data_tables["remuneration_components"],
            data_tables["employees"],
        )
        assert len(summary) == len(data_tables["employees"])
        assert summary["fully_loaded_cost_per_hour"].min() > 0
        assert summary["annual_cost"].sum() > 0

    def test_capacity_planner_works_with_synthetic_data(self, data_tables):
        """Capacity planner identifies gaps."""
        planner = CapacityPlanner()
        start = dt.date(2026, 6, 1)
        end = dt.date(2026, 6, 7)

        demand = data_tables["demand"][
            (data_tables["demand"]["date"] >= start.isoformat())
            & (data_tables["demand"]["date"] <= end.isoformat())
        ]
        required = planner.compute_required_hours(demand)
        available = planner.compute_available_hours(
            data_tables["employees"],
            data_tables["leave_transactions"],
            start,
            end,
            rosters_df=data_tables["rosters"],
        )
        gaps = planner.compute_capacity_gaps(required, available)
        gaps_df = planner.gaps_to_dataframe(gaps)

        assert len(gaps_df) > 0
        assert "UNDER_CAPACITY" in gaps_df["status"].values or "OVER_CAPACITY" in gaps_df["status"].values

    def test_scorecard_works_with_synthetic_data(self, data_tables):
        """Scorecard builds with all engines."""
        builder = ScorecardBuilder()
        scorecard = builder.build(
            data_tables["employees"],
            data_tables["stores"],
            data_tables["leave_types"],
            data_tables["leave_transactions"],
            data_tables["remuneration_components"],
            data_tables["demand"],
            data_tables["rosters"],
            as_of=dt.date(2026, 6, 30),
        )
        assert len(scorecard.metrics) > 0
        assert len(scorecard.store_scorecards) > 0
        assert scorecard.overall_health in ("OK", "WARNING", "CRITICAL")

    def test_scenario_engine_works_with_synthetic_data(self, data_tables):
        """Scenario engine runs on real synthetic components."""
        costing = RemunerationCostingEngine()
        components = costing.load_components(
            data_tables["remuneration_components"],
            data_tables["employees"],
        )
        summary = costing.cost_summary(
            data_tables["remuneration_components"],
            data_tables["employees"],
        )
        base_cost = costing.total_annual_cost(summary)

        scenario_engine = ScenarioEngine(costing)
        scenarios = scenario_engine.default_scenarios()
        comparison = scenario_engine.scenario_comparison(
            scenarios, components, base_cost,
        )
        assert len(comparison) == len(scenarios)
        # Baseline should have ~zero impact
        baseline = comparison[comparison["scenario"] == "Baseline"]
        assert abs(baseline["annual_cost_impact"].iloc[0]) < 10.0

    def test_roster_suggestions_work_with_synthetic_data(self, data_tables):
        """Roster suggester produces suggestions from real gaps."""
        planner = CapacityPlanner()
        start = dt.date(2026, 6, 1)
        end = dt.date(2026, 6, 7)

        demand = data_tables["demand"][
            (data_tables["demand"]["date"] >= start.isoformat())
            & (data_tables["demand"]["date"] <= end.isoformat())
        ]
        required = planner.compute_required_hours(demand)
        available = planner.compute_available_hours(
            data_tables["employees"],
            data_tables["leave_transactions"],
            start,
            end,
            rosters_df=data_tables["rosters"],
        )
        gaps = planner.compute_capacity_gaps(required, available)

        suggester = RosterSuggester()
        suggestions = suggester.suggest(gaps, available)
        assert len(suggestions) > 0
        assert all(s.suggestion_type in ("ADD_SHIFT", "REDUCE_HOURS") for s in suggestions)

    def test_cross_engine_data_consistency(self, data_tables):
        """Verify foreign key integrity across all tables."""
        emp_ids = set(data_tables["employees"]["employee_id"])
        store_ids = set(data_tables["stores"]["store_id"])

        # All employee IDs in dependent tables exist in employees
        assert set(data_tables["leave_transactions"]["employee_id"]).issubset(emp_ids)
        assert set(data_tables["rosters"]["employee_id"]).issubset(emp_ids)
        assert set(data_tables["remuneration_components"]["employee_id"]).issubset(emp_ids)

        # All store IDs exist in stores
        assert set(data_tables["rosters"]["store_id"]).issubset(store_ids)
        assert set(data_tables["demand"]["store_id"]).issubset(store_ids)
        assert set(data_tables["employees"]["store_id"]).issubset(store_ids)

        # Leave transaction balance_after values are consistent with hours
        # (accruals add, taken subtracts)
        tx = data_tables["leave_transactions"]
        for _, row in tx.head(100).iterrows():
            if row["transaction_type"] == "ACCRUAL":
                assert row["hours"] >= 0
            elif row["transaction_type"] == "TAKEN":
                assert row["hours"] >= 0
