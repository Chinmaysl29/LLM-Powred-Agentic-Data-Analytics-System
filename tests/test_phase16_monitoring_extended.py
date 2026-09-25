"""Additional Phase 16.4 lifecycle tests."""

from backend.monitoring.alerts import AlertManager, AlertRule, AlertSeverity
from backend.monitoring.dashboard_metrics import DashboardMetrics
from backend.monitoring.tracing import Tracer


def test_alert_suppression_and_threshold_validation():
    alerts = AlertManager()
    alerts.add_rule(AlertRule("latency", 1.0, AlertSeverity.WARNING, cooldown_seconds=60))
    assert alerts.evaluate("latency", 0.9) is None
    assert alerts.evaluate("latency", 1.1) is not None
    assert alerts.evaluate("latency", 1.2) is None


def test_trace_and_business_metric_aggregation():
    trace = Tracer()
    with trace.start_span("dataset-upload") as span:
        assert span.trace_id
    assert trace.spans[-1].duration_seconds is not None

    metrics = DashboardMetrics()
    metrics.record("datasets_uploaded", 2)
    metrics.record("datasets_uploaded")
    assert metrics.aggregate()["datasets_uploaded"] == 3
