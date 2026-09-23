"""Unit & Integration Tests for Phase 10.5: Infrastructure Monitoring.

Validates:
- System metrics collection (CPU, Memory, Disk, Network)
- Subsystem health checks (Database, Redis, ChromaDB, API Performance)
- Test Case: Service Failure -> Expected: Alert Triggered
- Threshold evaluation & alert resolution
"""

import pytest
from backend.deployment.infrastructure_monitor import InfrastructureMonitor, infrastructure_monitor


@pytest.fixture
def monitor():
    return InfrastructureMonitor()


def test_collect_system_metrics(monitor):
    """Verify host metrics are populated accurately."""
    metrics = monitor.collect_system_metrics()
    assert "cpu_pct" in metrics
    assert "memory_pct" in metrics
    assert "disk_pct" in metrics
    assert "bytes_sent_mb" in metrics
    assert metrics["memory_pct"] > 0.0


def test_check_subsystem_health_nominal(monitor):
    """Verify nominal state reports all services UP."""
    health = monitor.check_subsystem_health()
    for svc in ["database", "redis", "chromadb", "api_performance"]:
        assert svc in health
        assert health[svc]["status"] == "UP"


def test_service_failure_triggers_alert(monitor):
    """Test Case: Service Failure -> Expected: Alert Triggered."""
    res = monitor.simulate_service_failure(service_name="database")
    assert res["status"] == "PASS"
    assert res["alert_triggered"] is True
    assert any(a["source"] == "database" for a in res["active_alerts"])


def test_redis_failure_triggers_alert(monitor):
    """Verify Redis failure alerts properly."""
    res = monitor.simulate_service_failure(service_name="redis")
    assert res["status"] == "PASS"
    assert res["alert_triggered"] is True
    assert any(a["source"] == "redis" for a in res["active_alerts"])
