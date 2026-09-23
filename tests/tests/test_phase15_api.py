"""Integration coverage for the Phase 15 operator API."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_autonomous_operator_api_runs_a_safe_cycle(client):
    status_response = client.get("/api/v1/autonomous/status")
    assert status_response.status_code == 200
    assert status_response.json()["system_state"] == "RUNNING"
    assert status_response.json()["knowledge_nodes"] >= 15

    event_response = client.post(
        "/api/v1/autonomous/events",
        json={"event": {"type": "revenue_alert", "metric": "Revenue", "value": -0.08}},
    )
    assert event_response.status_code == 202
    assert event_response.json()["status"] == "QUEUED"

    cycle_response = client.post(
        "/api/v1/autonomous/cycles",
        json={"kpi_snapshot": {"revenue_change_pct": -0.08, "churn_rate": 0.10}},
    )
    assert cycle_response.status_code == 200
    cycle = cycle_response.json()
    assert len(cycle["phases_completed"]) == 6
    assert cycle["workflows_triggered"] >= 1

    intelligence_response = client.get("/api/v1/autonomous/intelligence")
    assert intelligence_response.status_code == 200
    assert "knowledge_graph" in intelligence_response.json()


def test_autonomous_simulation_and_graph_endpoints(client):
    simulation_response = client.post(
        "/api/v1/autonomous/simulate",
        json={"goal": "Reduce churn below two percent"},
    )
    assert simulation_response.status_code == 200
    assert len(simulation_response.json()) >= 2

    graph_response = client.get("/api/v1/autonomous/knowledge-graph")
    assert graph_response.status_code == 200
    assert len(graph_response.json()["nodes"]) >= 15
