"""Integration tests for Phase 11 Operations REST API."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_api_submit_feedback(client):
    """POST /api/v1/operations/feedback"""
    response = client.post(
        "/api/v1/operations/feedback",
        json={
            "description": "The report export button is unresponsive",
            "channel": "dashboard",
            "user_id": "test_user_api",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["feedback_type"] in ["PERFORMANCE", "BUG"]
    assert "fb_" in data["feedback_id"]


def test_api_get_feedback_analytics(client):
    """GET /api/v1/operations/feedback/analytics"""
    response = client.get("/api/v1/operations/feedback/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "total_feedback" in data
    assert "category_breakdown" in data


def test_api_record_and_get_analytics(client):
    """POST /api/v1/operations/analytics/events & GET /api/v1/operations/analytics/metrics"""
    post_res = client.post(
        "/api/v1/operations/analytics/events",
        json={
            "event_type": "query_executed",
            "user_id": "user_api_tester",
            "metadata": {"execution_time_ms": 150},
        },
    )
    assert post_res.status_code == 201
    assert "ev_" in post_res.json()["event_id"]

    get_res = client.get("/api/v1/operations/analytics/metrics")
    assert get_res.status_code == 200
    metrics = get_res.json()
    assert "daily_active_users" in metrics
    assert "queries_executed" in metrics


def test_api_quality_status(client):
    """GET /api/v1/operations/quality/status"""
    response = client.get("/api/v1/operations/quality/status")
    assert response.status_code == 200
    data = response.json()
    assert "quality_score" in data
    assert "alert_threshold" in data


def test_api_feature_flags(client):
    """GET /api/v1/operations/feature-flags & evaluate"""
    list_res = client.get("/api/v1/operations/feature-flags")
    assert list_res.status_code == 200
    assert len(list_res.json()["flags"]) >= 1

    eval_res = client.get("/api/v1/operations/feature-flags/new_dashboard_widgets/evaluate")
    assert eval_res.status_code == 200
    assert eval_res.json()["enabled"] is True


def test_api_costs(client):
    """GET /api/v1/operations/costs"""
    response = client.get("/api/v1/operations/costs")
    assert response.status_code == 200
    data = response.json()
    assert "monthly_cost" in data
    assert "recommendations" in data


def test_api_dashboard(client):
    """GET /api/v1/operations/dashboard"""
    response = client.get("/api/v1/operations/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "dashboard" in data
    assert "system_health" in data["dashboard"]


def test_api_orchestrator_status(client):
    """GET /api/v1/operations/orchestrator/status"""
    response = client.get("/api/v1/operations/orchestrator/status")
    assert response.status_code == 200
    data = response.json()
    assert "platform_health" in data
    assert "improvement_plan" in data
