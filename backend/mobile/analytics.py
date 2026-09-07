"""
Phase 12.8.9 — Mobile Analytics Module
Telemetry engine tracking mobile app usage, feature engagement, session duration,
frame rendering latency, network response times, and native crash diagnostics.
"""

from typing import Dict, Any, List, Optional
import time
import uuid
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.mobile.analytics")


class MobileTelemetryEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str
    event_name: str # "screen_view", "feature_used", "voice_query", "report_export"
    properties: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class MobilePerformanceMetric(BaseModel):
    metric_name: str # "time_to_first_kpi", "chart_render_ms", "api_latency_ms"
    value: float
    unit: str        # "ms", "fps", "mb"
    device_id: str
    timestamp: float = Field(default_factory=time.time)


class MobileCrashReport(BaseModel):
    crash_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    user_id: str
    os_version: str
    exception_type: str
    stack_trace: str
    occurred_at: float = Field(default_factory=time.time)


class MobileAnalyticsEngine:
    """
    Collects mobile telemetry, tracks session lengths, aggregates feature metrics,
    and logs crash diagnostics.
    """

    def __init__(self):
        self._events: List[MobileTelemetryEvent] = []
        self._metrics: List[MobilePerformanceMetric] = []
        self._crash_reports: List[MobileCrashReport] = []
        self._session_durations: Dict[str, float] = {}

    def track_event(
        self,
        session_id: str,
        user_id: str,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> MobileTelemetryEvent:
        """Log a user interaction or screen view event."""
        ev = MobileTelemetryEvent(
            session_id=session_id,
            user_id=user_id,
            event_name=event_name,
            properties=properties or {}
        )
        self._events.append(ev)
        return ev

    def record_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        device_id: str
    ) -> MobilePerformanceMetric:
        """Record network or rendering performance metric."""
        metric = MobilePerformanceMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            device_id=device_id
        )
        self._metrics.append(metric)
        return metric

    def record_session_duration(self, session_id: str, duration_sec: float):
        """Record total duration of active user session."""
        self._session_durations[session_id] = duration_sec

    def log_crash(
        self,
        session_id: str,
        user_id: str,
        os_version: str,
        exception_type: str,
        stack_trace: str
    ) -> MobileCrashReport:
        """Ingest native or unhandled JS exception stack trace."""
        crash = MobileCrashReport(
            session_id=session_id,
            user_id=user_id,
            os_version=os_version,
            exception_type=exception_type,
            stack_trace=stack_trace
        )
        self._crash_reports.append(crash)
        logger.error("Mobile crash reported for session %s: %s", session_id, exception_type)
        return crash

    def get_summary(self) -> Dict[str, Any]:
        """Aggregate high-level mobile telemetry metrics."""
        feature_counts = {}
        for ev in self._events:
            feature_counts[ev.event_name] = feature_counts.get(ev.event_name, 0) + 1

        avg_latencies = [m.value for m in self._metrics if "latency" in m.metric_name]
        mean_latency = round(sum(avg_latencies) / len(avg_latencies), 2) if avg_latencies else 0.0

        return {
            "total_events": len(self._events),
            "feature_usage": feature_counts,
            "recorded_metrics_count": len(self._metrics),
            "mean_api_latency_ms": mean_latency,
            "total_crashes": len(self._crash_reports),
            "tracked_sessions": len(self._session_durations)
        }
