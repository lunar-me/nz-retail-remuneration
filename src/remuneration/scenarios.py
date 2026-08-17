"""Scenario modelling engine for remuneration packages.

Allows modelling "what-if" package changes (extra leave days, higher
insurance, KiwiSaver rate changes, flexibility premium changes) and
quantifies the cost impact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

from .costing import RemunerationCostingEngine
from .models import RemunerationComponents, Scenario


@dataclass
class ScenarioResult:
    """Result of running a scenario against the workforce."""

    scenario: Scenario
    total_annual_cost: float
    annual_cost_impact: float
    total_hourly_rate: float
    avg_fully_loaded_rate: float
    per_employee_annual_impact: float
    headcount: int


class ScenarioEngine:
    """Runs scenarios against remuneration cost profiles."""

    def __init__(self, costing_engine: Optional[RemunerationCostingEngine] = None):
        """Initialise the scenario engine.

        Parameters
        ----------
        costing_engine : Optional[RemunerationCostingEngine]
            The underlying costing engine. If ``None``, a default is created.
        """
        self.costing = costing_engine or RemunerationCostingEngine()

    # ------------------------------------------------------------------
    # Scenario execution
    # ------------------------------------------------------------------
    def run_scenario(
        self,
        scenario: Scenario,
        components: Dict[int, RemunerationComponents],
        base_annual_cost: float,
    ) -> ScenarioResult:
        """Run a single scenario against the workforce.

        Parameters
        ----------
        scenario : Scenario
            The scenario to model.
        components : Dict[int, RemunerationComponents]
            Current remuneration components for all employees.
        base_annual_cost : float
            The current (baseline) total annual cost.

        Returns
        -------
        ScenarioResult
            The scenario's cost impact.
        """
        # Apply scenario adjustments to each employee's components
        adjusted_components = {
            emp_id: scenario.apply_to(comp)
            for emp_id, comp in components.items()
        }

        # Compute new total annual cost
        total_annual = sum(
            comp.annual_cost for comp in adjusted_components.values()
        )
        headcount = len(adjusted_components)

        # Compute hourly aggregates
        total_hours = sum(
            comp.contracted_hours_per_week * 52.0
            for comp in adjusted_components.values()
        )
        avg_rate = (
            total_annual / total_hours if total_hours > 0 else 0.0
        )

        return ScenarioResult(
            scenario=scenario,
            total_annual_cost=total_annual,
            annual_cost_impact=total_annual - base_annual_cost,
            total_hourly_rate=total_annual / (total_hours if total_hours > 0 else 1.0),
            avg_fully_loaded_rate=avg_rate,
            per_employee_annual_impact=(
                (total_annual - base_annual_cost) / headcount
                if headcount > 0
                else 0.0
            ),
            headcount=headcount,
        )

    def run_all_scenarios(
        self,
        scenarios: List[Scenario],
        components: Dict[int, RemunerationComponents],
        base_annual_cost: float,
    ) -> List[ScenarioResult]:
        """Run multiple scenarios.

        Parameters
        ----------
        scenarios : List[Scenario]
            Scenarios to model.
        components : Dict[int, RemunerationComponents]
            Current remuneration components.
        base_annual_cost : float
            Current total annual cost (baseline).

        Returns
        -------
        List[ScenarioResult]
            Results for each scenario.
        """
        return [
            self.run_scenario(s, components, base_annual_cost)
            for s in scenarios
        ]

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def scenarios_to_dataframe(
        self,
        results: List[ScenarioResult],
    ) -> pd.DataFrame:
        """Convert scenario results to a summary DataFrame.

        Parameters
        ----------
        results : List[ScenarioResult]
            Scenario results.

        Returns
        -------
        pd.DataFrame
            Summary table for reporting.
        """
        rows = []
        for r in results:
            rows.append(
                {
                    "scenario": r.scenario.name,
                    "description": r.scenario.description,
                    "total_annual_cost": round(r.total_annual_cost, 2),
                    "annual_cost_impact": round(r.annual_cost_impact, 2),
                    "pct_impact": round(
                        (r.annual_cost_impact / r.total_annual_cost * 100)
                        if r.total_annual_cost != 0
                        else 0.0,
                        2,
                    ),
                    "avg_fully_loaded_rate": round(r.avg_fully_loaded_rate, 2),
                    "per_employee_annual_impact": round(r.per_employee_annual_impact, 2),
                    "headcount": r.headcount,
                }
            )
        return pd.DataFrame(rows)

    def scenario_comparison(
        self,
        scenarios: List[Scenario],
        components: Dict[int, RemunerationComponents],
        base_annual_cost: float,
    ) -> pd.DataFrame:
        """Run scenarios and return a comparison table.

        Convenience wrapper around :meth:`run_all_scenarios` +
        :meth:`scenarios_to_dataframe`.

        Parameters
        ----------
        scenarios : List[Scenario]
            Scenarios to model.
        components : Dict[int, RemunerationComponents]
            Current remuneration components.
        base_annual_cost : float
            Current total annual cost.

        Returns
        -------
        pd.DataFrame
            Comparison table.
        """
        results = self.run_all_scenarios(scenarios, components, base_annual_cost)
        return self.scenarios_to_dataframe(results)

    # ------------------------------------------------------------------
    # Built-in scenarios
    # ------------------------------------------------------------------
    @staticmethod
    def default_scenarios() -> List[Scenario]:
        """Return a set of illustrative default scenarios.

        Returns
        -------
        List[Scenario]
            A set of common package-change scenarios.
        """
        return [
            Scenario(
                name="Baseline",
                description="Current package — no changes.",
            ),
            Scenario(
                name="+2 Days Annual Leave",
                description="Increase annual leave by 2 days (value of leave loading).",
                annual_leave_extra_days=2.0,
                leave_loading_rate=0.10,
            ),
            Scenario(
                name="+5 Days Sick Leave",
                description="Increase sick leave to 15 days/year.",
                sick_leave_extra_days=5.0,
                leave_loading_rate=0.11,
            ),
            Scenario(
                name="Higher Insurance (+$20/mo)",
                description="Increase employer insurance contribution by $20/month.",
                insurance_adjustment=20.0,
            ),
            Scenario(
                name="Higher KiwiSaver (4%)",
                description="Increase employer KiwiSaver contribution to 4%.",
                kiwisaver_rate=0.04,
            ),
            Scenario(
                name="Flex Premium +2%",
                description="Increase flexibility premium cap from 6% to 8%.",
                flexibility_premium_max=0.08,
            ),
            Scenario(
                name="Comprehensive Package",
                description="All enhancements combined: +2 days leave, +5 sick days, "
                            "+$20 insurance, 4% KiwiSaver, 8% flex cap.",
                annual_leave_extra_days=2.0,
                sick_leave_extra_days=5.0,
                insurance_adjustment=20.0,
                kiwisaver_rate=0.04,
                flexibility_premium_max=0.08,
            ),
        ]