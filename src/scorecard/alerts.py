"""Alerting rules engine for the integrated scorecard."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from .models import Alert, ProgrammeMetric, StoreMetric


class AlertEngine:
    """Raises exception alerts based on metric health."""

    def __init__(self):
        """Initialise the alert engine."""

    # ------------------------------------------------------------------
    # Programme-level alerts
    # ------------------------------------------------------------------
    def programme_alerts(
        self,
        metrics: List[ProgrammeMetric],
    ) -> List[Alert]:
        """Generate alerts from programme-level metrics.

        Parameters
        ----------
        metrics : List[ProgrammeMetric]
            Programme metrics from :class:`MetricCalculator`.

        Returns
        -------
        List[Alert]
            Generated alerts.
        """
        alerts: List[Alert] = []
        metric_map = {m.metric_name: m for m in metrics}

        # Leave liability
        if "avg_annual_leave_balance_days" in metric_map:
            m = metric_map["avg_annual_leave_balance_days"]
            if m.status != "OK":
                alerts.append(Alert(
                    alert_type="leave_liability",
                    severity=_severity_from_status(m.status),
                    message=(
                        f"Average annual leave balance is {m.metric_value:.1f} days "
                        f"— may indicate rising leave liability"
                    ),
                    metric_name=m.metric_name,
                    metric_value=m.metric_value,
                    threshold=30.0,
                ))

        # Insurance take-up
        if "insurance_takeup_rate" in metric_map:
            m = metric_map["insurance_takeup_rate"]
            if m.status != "OK":
                alerts.append(Alert(
                    alert_type="insurance_takeup",
                    severity=_severity_from_status(m.status),
                    message=(
                        f"Insurance take-up is {m.metric_value:.0%} "
                        f"— below target of 40%"
                    ),
                    metric_name=m.metric_name,
                    metric_value=m.metric_value,
                    threshold=0.40,
                ))

        # Flexibility utilisation
        if "avg_flexibility_preference" in metric_map:
            m = metric_map["avg_flexibility_preference"]
            if m.status != "OK":
                alerts.append(Alert(
                    alert_type="flexibility_utilisation",
                    severity=_severity_from_status(m.status),
                    message=(
                        f"Average flexibility preference is {m.metric_value:.2f} "
                        f"— may limit roster flexibility"
                    ),
                    metric_name=m.metric_name,
                    metric_value=m.metric_value,
                    threshold=0.40,
                ))

        return alerts

    # ------------------------------------------------------------------
    # Store-level alerts
    # ------------------------------------------------------------------
    def store_alerts(
        self,
        store_metrics: List[StoreMetric],
    ) -> List[Alert]:
        """Generate alerts from store-level metrics.

        Parameters
        ----------
        store_metrics : List[StoreMetric]
            Store metrics from :class:`MetricCalculator`.

        Returns
        -------
        List[Alert]
            Generated alerts.
        """
        alerts: List[Alert] = []

        # Group metrics by store
        by_store: dict = {}
        for m in store_metrics:
            by_store.setdefault(m.store_id, []).append(m)

        for store_id, metrics in by_store.items():
            metric_map = {m.metric_name: m for m in metrics}

            # Capacity ratio
            if "capacity_ratio" in metric_map:
                m = metric_map["capacity_ratio"]
                if m.status != "OK":
                    alerts.append(Alert(
                        alert_type="capacity",
                        severity=_severity_from_status(m.status),
                        store_id=store_id,
                        message=(
                            f"Store {store_id} capacity ratio is {m.metric_value:.2f} "
                            f"— {m.notes}"
                        ),
                        metric_name=m.metric_name,
                        metric_value=m.metric_value,
                        threshold=0.9,
                    ))

            # Insurance take-up
            if "insurance_takeup" in metric_map:
                m = metric_map["insurance_takeup"]
                if m.status != "OK":
                    alerts.append(Alert(
                        alert_type="insurance_takeup",
                        severity=_severity_from_status(m.status),
                        store_id=store_id,
                        message=(
                            f"Store {store_id} insurance take-up is {m.metric_value:.0%}"
                        ),
                        metric_name=m.metric_name,
                        metric_value=m.metric_value,
                        threshold=0.40,
                    ))

            # Tight capacity flag
            if "tight_capacity_store" in metric_map:
                m = metric_map["tight_capacity_store"]
                if m.status != "OK":
                    alerts.append(Alert(
                        alert_type="tight_capacity",
                        severity="MEDIUM",
                        store_id=store_id,
                        message=f"Store {store_id} is flagged as structurally tight on capacity",
                        metric_name=m.metric_name,
                        metric_value=m.metric_value,
                        threshold=1.0,
                    ))

        return alerts

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def alerts_to_dataframe(self, alerts: List[Alert]):
        """Convert alerts to a DataFrame for reporting."""
        import pandas as pd

        rows = [a.to_dict() for a in alerts]
        if not rows:
            return pd.DataFrame(
                columns=[
                    "alert_type", "severity", "store_id", "message",
                    "metric_name", "metric_value", "threshold", "date",
                ]
            )
        return pd.DataFrame(rows)


def _severity_from_status(status: str) -> str:
    """Map metric status to alert severity."""
    if status == "CRITICAL":
        return "CRITICAL"
    if status == "WARNING":
        return "HIGH"
    return "LOW"