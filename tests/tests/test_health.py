from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase
from backend.app.database.redis import RedisCache
from backend.main import app


def test_health_returns_dependency_details(monkeypatch: object) -> None:
    """The versioned health endpoint reports every required dependency."""
    monkeypatch.setattr(PostgresDatabase, "connect", lambda self: None)
    monkeypatch.setattr(PostgresDatabase, "health_check", AsyncMock(return_value=(True, "PostgreSQL is reachable")))
    monkeypatch.setattr(RedisCache, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "health_check", AsyncMock(return_value=(True, "Redis is reachable")))
    monkeypatch.setattr(ChromaDatabase, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "health_check", AsyncMock(return_value=(True, "ChromaDB is reachable")))

    with TestClient(app) as client:
        response = client.get("/api/v1/health", headers={"X-Request-ID": "health-test"})

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["postgresql"]["status"] == "healthy"
    assert response.headers["X-Request-ID"] == "health-test"
    assert "X-Process-Time-Ms" in response.headers
