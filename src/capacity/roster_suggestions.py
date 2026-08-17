"""Roster suggestion engine.

Generates basic roster adjustments to address capacity gaps, respecting
employee flexibility preferences where possible.
"""

from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

from .models import AvailableHours, CapacityGap, RosterSuggestion


class RosterSuggester:
    """Generates roster suggestions to address capacity gaps."""

    def __init__(
        self,
        *,
        min_gap_hours: float = 2.0,
        flexibility_threshold: float = 0.6,
    ):
        """Initialise the roster suggester.

        Parameters
        ----------
        min_gap_hours : float, optional
            Minimum gap hours to generate a suggestion (default 2.0).
        flexibility_threshold : float, optional
            Minimum flexibility score to suggest an employee for a
            gap-filling shift (default 0.6).
        """
        self.min_gap_hours = min_gap_hours
        self.flexibility_threshold = flexibility_threshold

    def suggest(
        self,
        gaps: List[CapacityGap],
        available: List[AvailableHours],
    ) -> List[RosterSuggestion]:
        """Generate roster suggestions for capacity gaps.

        Parameters
        ----------
        gaps : List[CapacityGap]
            Capacity gaps from the capacity planner.
        available : List[AvailableHours]
            Available hours per employee-day.

        Returns
        -------
        List[RosterSuggestion]
            Suggested roster adjustments.
        """
        # Build lookup of available employees by store-day-role
        avail_by_key: Dict[tuple, List[AvailableHours]] = {}
        for a in available:
            key = (a.store_id, a.date, a.role)
            avail_by_key.setdefault(key, []).append(a)

        suggestions: List[RosterSuggestion] = []
        for gap in gaps:
            if gap.status == "BALANCED":
                continue

            if gap.gap_hours > self.min_gap_hours:
                # Under-capacity: suggest adding hours
                key = (gap.store_id, gap.date, gap.role)
                candidates = avail_by_key.get(key, [])

                # Prefer high-flexibility employees
                candidates_sorted = sorted(
                    candidates,
                    key=lambda a: a.flexibility_preference,
                    reverse=True,
                )

                if candidates_sorted:
                    best = candidates_sorted[0]
                    rationale = (
                        f"High flexibility preference ({best.flexibility_preference:.2f})"
                        if best.flexibility_preference >= self.flexibility_threshold
                        else "Available employee (limited flexibility)"
                    )
                    suggestions.append(
                        RosterSuggestion(
                            store_id=gap.store_id,
                            date=gap.date,
                            role=gap.role,
                            gap_hours=gap.gap_hours,
                            suggested_employee_id=best.employee_id,
                            suggestion_type="ADD_SHIFT",
                            rationale=rationale,
                        )
                    )
                else:
                    suggestions.append(
                        RosterSuggestion(
                            store_id=gap.store_id,
                            date=gap.date,
                            role=gap.role,
                            gap_hours=gap.gap_hours,
                            suggested_employee_id=None,
                            suggestion_type="ADD_SHIFT",
                            rationale="No available employee with this role — consider hiring/training",
                        )
                    )

            elif gap.gap_hours < -self.min_gap_hours:
                # Over-capacity: suggest reducing hours
                suggestions.append(
                    RosterSuggestion(
                        store_id=gap.store_id,
                        date=gap.date,
                        role=gap.role,
                        gap_hours=gap.gap_hours,
                        suggested_employee_id=None,
                        suggestion_type="REDUCE_HOURS",
                        rationale="Over-resourced — consider reducing hours or cross-training",
                    )
                )

        return suggestions

    def suggestions_to_dataframe(
        self,
        suggestions: List[RosterSuggestion],
    ):
        """Convert suggestions to a DataFrame for reporting."""
        import pandas as pd

        rows = [s.to_dict() for s in suggestions]
        return pd.DataFrame(rows)
