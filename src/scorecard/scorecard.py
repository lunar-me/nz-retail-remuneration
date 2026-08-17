"""Scorecard builder that combines all metrics and alerts."""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

import pandas as pd

from .alerts import AlertEngine
from .metrics import MetricCalculator
from .models import ProgrammeScorecard, StoreScorecard


class ScorecardBuilder:
    """Builds the integrated scorecard from synthetic data."""

    def __init__(
        self,
        metric_calculator: Optional[MetricCalculator] = None,
        alert_engine: Optional[AlertEngine] = None,
    ):
        """Initialise the scorecard builder.

        Parameters
        ----------
        metric_calculator : Optional[MetricCalculator]
            The metric calculator. If ``None``, a default is created.
        alert_engine : Optional[AlertEngine]
            The alert engine. If ``None``, a default is created.
        """
        self.metrics = metric_calculator or MetricCalculator()
        self.alerts = alert_engine or AlertEngine()

    def build(
        self,
        employees_df: pd.DataFrame,
        stores_df: pd.DataFrame,
        leave_types_df: pd.DataFrame,
        leave_tx_df: pd.DataFrame,
        remuneration_df: pd.DataFrame,
        demand_df: pd.DataFrame,
        rosters_df: pd.DataFrame,
        *,
        as_of: Optional[dt.date] = None,
    ) -> ProgrammeScorecard:
        """Build the complete scorecard.

        Parameters
        ----------
        employees_df : pd.DataFrame
            The ``employees`` table.
        stores_df : pd.DataFrame
            The ``stores`` table.
        leave_types_df : pd.DataFrame
            The ``leave_types`` table.
        leave_tx_df : pd.DataFrame
            The ``leave_transactions`` table.
        remuneration_df : pd.DataFrame
            The ``remuneration_components`` table.
        demand_df : pd.DataFrame
            The ``demand`` table.
        rosters_df : pd.DataFrame
            The ``rosters`` table.
        as_of : Optional[dt.date]
            As-of date.

        Returns
        -------
        ProgrammeScorecard
            The complete scorecard.
        """
        as_of = as_of or dt.date.today()

        # Programme metrics & alerts
        programme_metrics = self.metrics.programme_metrics(
            employees_df, leave_types_df, leave_tx_df, remuneration_df,
            as_of=as_of,
        )
        programme_alerts = self.alerts.programme_alerts(programme_metrics)

        # Store metrics & alerts
        store_metrics = self.metrics.store_metrics(
            employees_df, stores_df, leave_types_df, leave_tx_df,
            demand_df, rosters_df, as_of=as_of,
        )
        store_alerts = self.alerts.store_alerts(store_metrics)

        # Build store scorecards
        store_scorecards: List[StoreScorecard] = []
        by_store: dict = {}
        for m in store_metrics:
            by_store.setdefault(m.store_id, []).append(m)

        for store_id, metrics in by_store.items():
            store_alerts_for = [a for a in store_alerts if a.store_id == store_id]
            health = _overall_health(metrics)
            store_scorecards.append(StoreScorecard(
                store_id=store_id,
                metrics=metrics,
                alerts=store_alerts_for,
                overall_health=health,
            ))

        # Overall programme health
        all_metrics = list(programme_metrics) + list(store_metrics)
        overall = _overall_health(all_metrics)

        return ProgrammeScorecard(
            metrics=programme_metrics,
            alerts=programme_alerts + store_alerts,
            overall_health=overall,
            generated_at=dt.datetime.now(),
            store_scorecards=store_scorecards,
        )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def programme_metrics_to_dataframe(
        self,
        scorecard: ProgrammeScorecard,
    ):
        """Convert programme metrics to a DataFrame."""
        rows = [
            {
                "metric": m.metric_name,
                "value": m.metric_value,
                "unit": m.metric_unit,
                "status": m.status,
                "notes": m.notes,
            }
            for m in scorecard.metrics
        ]
        return pd.DataFrame(rows)

    def store_metrics_to_dataframe(
        self,
        scorecard: ProgrammeScorecard,
    ):
        """Convert store metrics to a DataFrame."""
        rows = []
        for store in scorecard.store_scorecards:
            for m in store.metrics:
                rows.append({
                    "store_id": store.store_id,
                    "metric": m.metric_name,
                    "value": m.metric_value,
                    "unit": m.metric_unit,
                    "status": m.status,
                    "notes": m.notes,
                })
        return pd.DataFrame(rows)

    def alerts_to_dataframe(
        self,
        scorecard: ProgrammeScorecard,
    ):
        """Convert alerts to a DataFrame."""
        return self.alerts.alerts_to_dataframe(scorecard.alerts)

    def render_text(self, scorecard: ProgrammeScorecard) -> str:
        """Render the scorecard as readable text.

        Parameters
        ----------
        scorecard : ProgrammeScorecard
            The scorecard to render.

        Returns
        -------
        str
            Text representation.
        """
        lines = [
            "=" * 60,
            "NZ RETAIL REMUNERATION & WORKFORCE SCORECARD",
            "=" * 60,
            f"Generated: {scorecard.generated_at.isoformat() if scorecard.generated_at else 'N/A'}",
            f"Overall health: {scorecard.overall_health}",
            "",
            "--- Programme Metrics ---",
        ]
        for m in scorecard.metrics:
            lines.append(
                f"  {m.metric_name:40s} {m.metric_value:>10,.1f} {m.metric_unit:8s} [{m.status}]"
            )

        lines.append("")
        lines.append("--- Store Scorecards ---")
        for store in scorecard.store_scorecards:
            lines.append(f"  Store {store.store_id}: {store.overall_health} ({len(store.alerts)} alerts)")
            for m in store.metrics:
                if m.metric_name in ("headcount", "capacity_ratio", "insurance_takeup"):
                    lines.append(f"    {m.metric_name:25s} {m.metric_value:>10,.2f} {m.metric_unit:8s} [{m.status}]")

        lines.append("")
        lines.append(f"--- Alerts ({len(scorecard.alerts)}) ---")
        for a in scorecard.alerts:
            store_str = f"Store {a.store_id}" if a.store_id else "Programme"
            lines.append(f"  [{a.severity:8s}] {store_str}: {a.message}")

        return "\n".join(lines)


def _overall_health(metrics: list) -> str:
    """Determine overall health from a list of metrics."""
    statuses = [m.status for m in metrics]
    if any(s == "CRITICAL" for s in statuses):
        return "CRITICAL"
    if any(s == "WARNING" for s in statuses):
        return "WARNING"
    return "OK"