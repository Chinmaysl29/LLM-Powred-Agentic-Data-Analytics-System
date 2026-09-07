"""Phase 16.5 audit persistence contract and API tests."""

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.audit_trail_service import AuditTrailService


def test_audit_service_records_and_filters_fallback_entries():
    service = AuditTrailService()
    uploaded = service.record(actor="analyst@example.com", action="dataset.upload", resource_type="dataset", resource_id="ds-1")
    service.record(actor="analyst@example.com", action="forecast.request", resource_type="forecast", resource_id="fc-1")
    assert uploaded["actor"] == "analyst@example.com"
    assert uploaded["occurred_at"]
    entries = service.query(actor="analyst@example.com", action="dataset.upload")
    assert len(entries) == 1
    assert entries[0]["resource_id"] == "ds-1"


def test_audit_api_logs_and_queries_actions():
    client = TestClient(create_app())
    created = client.post(
        "/api/v1/audit",
        json={
            "actor": "operator@example.com",
            "action": "agent.execute",
            "resource_type": "agent",
            "resource_id": "forecast-agent",
            "details": {"job_id": "job-1"},
        },
    )
    assert created.status_code == 201
    assert created.json()["action"] == "agent.execute"
    queried = client.get("/api/v1/audit", params={"actor": "operator@example.com"})
    assert queried.status_code == 200
    assert any(entry["resource_type"] == "agent" for entry in queried.json())


def test_audit_api_search_export_and_event_lookup():
    client = TestClient(create_app())
    created = client.post("/api/v1/audit", json={
        "actor": "security@example.com", "action": "access.denied", "resource_type": "security",
        "status": "failed", "metadata": {"reason": "rbac"},
    })
    assert created.status_code == 201
    event = created.json()
    searched = client.get("/api/v1/audit/search", params={"search": "denied", "status": "failed"})
    assert searched.status_code == 200
    assert any(item["event_id"] == event["event_id"] for item in searched.json())
    assert client.get(f"/api/v1/audit/{event['id']}").status_code == 200
    exported = client.get("/api/v1/audit/export", params={"format": "csv", "actor": "security@example.com"})
    assert exported.status_code == 200
    assert "event_id" in exported.text
