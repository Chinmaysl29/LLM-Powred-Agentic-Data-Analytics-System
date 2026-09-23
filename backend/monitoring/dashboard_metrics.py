"""Business-metric aggregation used by API and Grafana dashboard queries."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from backend.monitoring.prometheus_metrics import platform_metrics


class DashboardMetrics:
    def __init__(self) -> None:
        self._events: list[tuple[datetime, str, int]] = []

    def record(self, event_type: str, count: int = 1) -> None:
        if count < 1:
            raise ValueError("count must be positive")
        self._events.append((datetime.now(timezone.utc), event_type, count))
        platform_metrics.record_business_event(event_type, count)

    def aggregate(self, since: datetime | None = None) -> dict[str, int]:
        totals: Counter[str] = Counter()
        for when, event, count in self._events:
            if since is None or when >= since:
                totals[event] += count
        return dict(totals)


dashboard_metrics = DashboardMetrics()
