"""Flexible Remuneration Costing & Scenario Model - Project 2.

Computes fully-loaded hourly/annual costs and models package changes
(base + leave value + insurance + flexibility).
"""

from .costing import RemunerationCostingEngine
from .scenarios import ScenarioEngine

__all__ = ["RemunerationCostingEngine", "ScenarioEngine"]