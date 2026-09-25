"""Tests for Phase 8.6: Monitoring & Observability."""

import time
import pytest
from backend.monitoring.metrics_collector import MetricsCollector


@pytest.fixture
def collector():
    mc = MetricsCollector()
    mc.clear()
    return mc


def test_service_health_output_schema(collector):
    """Verify output matches Phase 8 specifications."""
    rec = collector.record_service_health(service="forecasting", latency=240, status="healthy")
    assert rec["service"] == "forecasting"
    assert rec["latency"] == 240
    assert rec["status"] == "healthy"


def test_detect_latency_spikes_and_failure_events(collector):
    """Test Case: Detect latency spikes or failure events."""
    # Normal operations
    collector.record_service_health("database", latency=15, status="healthy")
    collector.record_service_health("forecasting", latency=300, status="healthy")

    # Spike event (latency > 1000ms)
    collector.record_service_health("analytics", latency=1850, status="healthy")

    # Failure event
    collector.record_service_health("llm", latency=50, status="unhealthy", error="Rate limit exceeded")

    anomalies = collector.detect_anomalies(latency_spike_threshold_ms=1000.0)
    assert len(anomalies) >= 2

    types = {a["type"] for a in anomalies}
    assert "latency_spike" in types
    assert "service_failure" in types

    spike = next(a for a in anomalies if a["type"] == "latency_spike")
    assert spike["service"] == "analytics"
    assert spike["latency"] == 1850

    failure = next(a for a in anomalies if a["type"] == "service_failure")
    assert failure["service"] == "llm"


def test_llm_token_usage_tracking(collector):
    """Verify token usage tracking."""
    usage = collector.record_token_usage(prompt_tokens=350, completion_tokens=150, model="gpt-4o", agent="sql_agent")
    assert usage["total_tokens"] == 500
    assert usage["model"] == "gpt-4o"

    health = collector.get_system_health()
    assert health["total_tokens_consumed"] == 500


def test_track_time_context_manager(collector):
    """Verify execution time tracking context manager."""
    with collector.track_time("database", "query_exec"):
        time.sleep(0.02)  # 20ms

    health = collector.get_system_health()
    db_health = health["services"]["database"]
    assert db_health["latency"] >= 15.0  # At least 15ms
    assert db_health["status"] == "healthy"
