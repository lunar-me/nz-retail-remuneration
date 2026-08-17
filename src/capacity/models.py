"""Data models for the capacity planner.

Defines dataclasses for labour requirements, capacity gaps, and
roster suggestions.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class LabourStandardsConfig:
    """Labour productivity standards per role family."""

    standards: Dict[str, float]

    def productivity_for(self, role: str) -> float:
        """Return the productivity standard (units per labour hour).

        Falls back to the default standard if role not found.
        """
        return self.standards.get(role, self.standards.get("default", 20.0))


@dataclass
class LabourRequirement:
    """Required labour hours for a store-day-role combination."""

    store_id: int
    date: dt.date
    role: str
    required_hours: float
    demand_index: float
    productivity: float


@dataclass
class AvailableHours:
    """Available labour hours for an employee on a given date."""

    employee_id: int
    store_id: int
    date: dt.date
    role: str
    contracted_hours: float
    leave_hours: float
    available_hours: float
    flexibility_preference: float


@dataclass
class CapacityGap:
    """Capacity gap for a store-day-role combination."""

    store_id: int
    date: dt.date
    role: str
    required_hours: float
    available_hours: float
    gap_hours: float  # positive = shortfall, negative = surplus
    gap_ratio: float  # available / required (1.0 = balanced)
    status: str  # "UNDER_CAPACITY" | "BALANCED" | "OVER_CAPACITY"


@dataclass
class RosterSuggestion:
    """A suggested roster adjustment."""

    store_id: int
    date: dt.date
    role: str
    gap_hours: float
    suggested_employee_id: Optional[int] = None
    suggestion_type: str = ""  # "ADD_SHIFT" | "MOVE_HOURS" | "REDUCE_HOURS"
    rationale: str = ""

    def to_dict(self) -> Dict:
        """Convert to a dict for reporting."""
        return {
            "store_id": self.store_id,
            "date": self.date.isoformat(),
            "role": self.role,
            "gap_hours": round(self.gap_hours, 1),
            "suggested_employee_id": self.suggested_employee_id,
            "suggestion_type": self.suggestion_type,
            "rationale": self.rationale,
        }