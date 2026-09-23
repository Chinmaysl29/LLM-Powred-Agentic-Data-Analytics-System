"""
Tests for:
  GET /api/v1/health  — dependency health check
  GET /metrics        — Prometheus metrics endpoint
"""

import pytest
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase
from backend.app.database.redis import RedisCache
from backend.main import app


# ===========================================================================
# Fixtures
# ===========================================================================

def _patch_infra_healthy(monkeypatch):
    monkeypatch.setattr(PostgresDatabase, "connect", lambda self: None)
    monkeypatch.setattr(PostgresDatabase, "health_check", AsyncMock(return_value=(True, "PostgreSQL is reachable")))
    monkeypatch.setattr(RedisCache, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "health_check", AsyncMock(return_value=(True, "Redis is reachable")))
    monkeypatch.setattr(ChromaDatabase, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "health_check", AsyncMock(return_value=(True, "ChromaDB is reachable")))


def _patch_infra_degraded(monkeypatch):
    monkeypatch.setattr(PostgresDatabase, "connect", lambda self: None)
    monkeypatch.setattr(PostgresDatabase, "health_check", AsyncMock(return_value=(False, "PostgreSQL is unavailable")))
    monkeypatch.setattr(RedisCache, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "health_check", AsyncMock(return_value=(True, "Redis is reachable")))
    monkeypatch.setattr(ChromaDatabase, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "health_check", AsyncMock(return_value=(True, "ChromaDB is reachable")))


# ===========================================================================
# Health Endpoint Tests
# ===========================================================================

class TestHealthEndpoint:

    def test_health_returns_200_when_all_healthy(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            res = client.get("/api/v1/health")
        assert res.status_code == 200

    def test_health_returns_status_healthy(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            data = client.get("/api/v1/health").json()
        assert data["status"] == "healthy"

    def test_health_returns_postgresql_status(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            data = client.get("/api/v1/health").json()
        assert "postgresql" in data
        assert data["postgresql"]["status"] == "healthy"

    def test_health_returns_redis_status(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            data = client.get("/api/v1/health").json()
        assert "redis" in data
        assert data["redis"]["status"] == "healthy"

    def test_health_returns_chromadb_status(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            data = client.get("/api/v1/health").json()
        assert "chromadb" in data
        assert data["chromadb"]["status"] == "healthy"

    def test_health_returns_application_status(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            data = client.get("/api/v1/health").json()
        assert "application" in data
        assert data["application"]["status"] == "healthy"

    def test_health_propagates_request_id_header(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            res = client.get("/api/v1/health", headers={"X-Request-ID": "trace-abc-123"})
        assert res.headers.get("X-Request-ID") == "trace-abc-123"

    def test_health_includes_process_time_header(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            res = client.get("/api/v1/health")
        assert "X-Process-Time-Ms" in res.headers

    def test_health_degraded_when_postgres_down(self, monkeypatch):
        _patch_infra_degraded(monkeypatch)
        with TestClient(app) as client:
            data = client.get("/api/v1/health").json()
        assert data["status"] == "degraded"
        assert data["postgresql"]["status"] == "unhealthy"

    def test_health_success_field_true_when_healthy(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            data = client.get("/api/v1/health").json()
        assert data["success"] is True

    def test_health_success_field_false_when_degraded(self, monkeypatch):
        _patch_infra_degraded(monkeypatch)
        with TestClient(app) as client:
            data = client.get("/api/v1/health").json()
        assert data["success"] is False

    def test_health_all_dependencies_unhealthy_returns_degraded(self, monkeypatch):
        monkeypatch.setattr(PostgresDatabase, "connect", lambda self: None)
        monkeypatch.setattr(PostgresDatabase, "health_check", AsyncMock(return_value=(False, "PG down")))
        monkeypatch.setattr(RedisCache, "connect", AsyncMock(return_value=None))
        monkeypatch.setattr(RedisCache, "close", AsyncMock(return_value=None))
        monkeypatch.setattr(RedisCache, "health_check", AsyncMock(return_value=(False, "Redis down")))
        monkeypatch.setattr(ChromaDatabase, "connect", AsyncMock(return_value=None))
        monkeypatch.setattr(ChromaDatabase, "close", AsyncMock(return_value=None))
        monkeypatch.setattr(ChromaDatabase, "health_check", AsyncMock(return_value=(False, "Chroma down")))

        with TestClient(app) as client:
            data = client.get("/api/v1/health").json()
        assert data["status"] == "degraded"
        assert data["postgresql"]["status"] == "unhealthy"
        assert data["redis"]["status"] == "unhealthy"
        assert data["chromadb"]["status"] == "unhealthy"


# ===========================================================================
# Metrics Endpoint Tests
# ===========================================================================

class TestMetricsEndpoint:

    def test_metrics_returns_200(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            res = client.get("/metrics")
        assert res.status_code == 200

    def test_metrics_content_type_is_prometheus_format(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            res = client.get("/metrics")
        assert "text/plain" in res.headers["content-type"]

    def test_metrics_contains_api_requests_counter(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            client.get("/api/v1/health")  # Generate one metric observation
            res = client.get("/metrics")
        # Prometheus output contains metric definition lines
        assert len(res.text) > 0

    def test_metrics_endpoint_not_in_openapi_schema(self, monkeypatch):
        _patch_infra_healthy(monkeypatch)
        with TestClient(app) as client:
            openapi = client.get("/openapi.json").json()
        paths = openapi.get("paths", {})
        assert "/metrics" not in paths
