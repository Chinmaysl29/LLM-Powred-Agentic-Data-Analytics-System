"""Phase 16.4 Prometheus metric exposure and collection tests."""

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.monitoring.prometheus_metrics import platform_metrics


def test_prometheus_metrics_are_exposed_and_collected():
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "ai_analyst_api_requests_total" in metrics.text
        assert "ai_analyst_dependency_up" in metrics.text


def test_agent_and_job_metrics_are_recorded():
    platform_metrics.record_agent_execution("forecasting", "success")
    platform_metrics.record_job_event("forecast", "completed")
    rendered = platform_metrics.render().decode("utf-8")
    assert 'agent="forecasting",outcome="success"' in rendered
    assert 'job_type="forecast",status="completed"' in rendered
