"""Data models for the integrated scorecard."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StoreMetric:
    """A single metric value for a store."""

    store_id: int
    metric_name: str
    metric_value: float
    metric_unit: str = ""
    is_good: bool = True
    status: str = "OK"  # OK | WARNING | CRITICAL
    notes: str = ""


@dataclass
class ProgrammeMetric:
    """A programme-level metric value."""

    metric_name: str
    metric_value: float
    metric_unit: str = ""
    is_good: bool = True
    status: str = "OK"
    notes: str = ""


@dataclass
class Alert:
    """An exception alert raised by the alert engine."""

    alert_type: str
    severity: str  # LOW | MEDIUM | HIGH | CRITICAL
    store_id: Optional[int] = None
    message: str = ""
    metric_name: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0
    date: Optional[dt.date] = None

    def to_dict(self) -> Dict:
        """Convert to a dict for reporting."""
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "store_id": self.store_id,
            "message": self.message,
            "metric_name": self.metric_name,
            "metric_value": round(self.metric_value, 2) if self.metric_value else None,
            "threshold": round(self.threshold, 2) if self.threshold else None,
            "date": self.date.isoformat() if self.date else None,
        }


@dataclass
class StoreScorecard:
    """A store-level scorecard combining all metrics."""

    store_id: int
    metrics: List[StoreMetric] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
    overall_health: str = "OK"  # OK | WARNING | CRITICAL

    @property
    def metric_map(self) -> Dict[str, StoreMetric]:
        """Return metrics as a name-keyed dict."""
        return {m.metric_name: m for m in self.metrics}

    def to_dict(self) -> Dict:
        """Convert to a dict for reporting."""
        return {
            "store_id": self.store_id,
            "overall_health": self.overall_health,
            "metrics": {
                m.metric_name: {
                    "value": m.metric_value,
                    "unit": m.metric_unit,
                    "status": m.status,
                }
                for m in self.metrics
            },
            "alert_count": len(self.alerts),
        }


@dataclass
class ProgrammeScorecard:
    """The programme-level scorecard."""

    metrics: List[ProgrammeMetric] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
    overall_health: str = "OK"
    generated_at: Optional[dt.datetime] = None
    store_scorecards: List[StoreScorecard] = field(default_factory=list)

    @property
    def metric_map(self) -> Dict[str, ProgrammeMetric]:
        """Return metrics as a name-keyed dict."""
        return {m.metric_name: m for m in self.metrics}