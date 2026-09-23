"""
Tests for authentication API endpoints:
  POST /api/v1/auth/register
  POST /api/v1/auth/login
  POST /api/v1/auth/refresh
  POST /api/v1/auth/logout
  GET  /api/v1/auth/profile
  GET  /api/v1/auth/me
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.security import hash_password
from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase, get_db_session
from backend.app.database.redis import RedisCache
from backend.app.models.base import Base
from backend.app.models.user import User
from backend.main import app
from backend.security.auth_service import AuthService


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def client(db_engine, monkeypatch):
    """TestClient with mocked infra and SQLite override."""
    monkeypatch.setattr(PostgresDatabase, "connect", lambda self: None)
    monkeypatch.setattr(PostgresDatabase, "health_check", AsyncMock(return_value=(True, "OK")))
    monkeypatch.setattr(RedisCache, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(RedisCache, "health_check", AsyncMock(return_value=(True, "OK")))
    monkeypatch.setattr(ChromaDatabase, "connect", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "close", AsyncMock(return_value=None))
    monkeypatch.setattr(ChromaDatabase, "health_check", AsyncMock(return_value=(True, "OK")))

    SessionFactory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)

    def _override_db():
        s = SessionFactory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db_session] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def db_session(db_engine):
    SessionFactory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    s = SessionFactory()
    yield s
    s.close()


@pytest.fixture(scope="function")
def registered_user(client):
    """Register a user and return the credentials."""
    payload = {
        "email": "testuser@example.com",
        "password": "SecurePass1!",
        "full_name": "Test User",
    }
    client.post("/api/v1/auth/register", json=payload)
    return payload


# ===========================================================================
# Register Tests
# ===========================================================================

class TestRegister:

    def test_register_new_user_returns_201(self, client):
        res = client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "Password123!",
            "full_name": "New User",
        })
        assert res.status_code == 201

    def test_register_returns_user_response(self, client):
        res = client.post("/api/v1/auth/register", json={
            "email": "user2@example.com",
            "password": "Password123!",
        })
        data = res.json()
        assert "id" in data
        assert data["email"] == "user2@example.com"
        assert data["is_active"] is True

    def test_register_default_role_is_analyst(self, client):
        res = client.post("/api/v1/auth/register", json={
            "email": "analyst@example.com",
            "password": "Password123!",
        })
        assert res.json()["role"] == "analyst"

    def test_register_duplicate_email_returns_409(self, client):
        payload = {"email": "dup@example.com", "password": "Password123!"}
        client.post("/api/v1/auth/register", json=payload)
        res = client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 409

    def test_register_invalid_email_returns_422(self, client):
        res = client.post("/api/v1/auth/register", json={
            "email": "ab",  # Too short
            "password": "Password123!",
        })
        assert res.status_code == 422

    def test_register_short_password_returns_422(self, client):
        res = client.post("/api/v1/auth/register", json={
            "email": "short@example.com",
            "password": "123",
        })
        assert res.status_code == 422

    def test_register_with_full_name(self, client):
        res = client.post("/api/v1/auth/register", json={
            "email": "fullname@example.com",
            "password": "Password123!",
            "full_name": "John Doe",
        })
        assert res.json()["full_name"] == "John Doe"

    def test_register_missing_required_field_returns_422(self, client):
        res = client.post("/api/v1/auth/register", json={"email": "x@x.com"})
        assert res.status_code == 422


# ===========================================================================
# Login Tests
# ===========================================================================

class TestLogin:

    def test_login_valid_credentials_returns_200(self, client, registered_user):
        res = client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert res.status_code == 200

    def test_login_returns_access_token(self, client, registered_user):
        res = client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        data = res.json()
        assert "access_token" in data
        assert len(data["access_token"]) > 10

    def test_login_returns_refresh_token(self, client, registered_user):
        res = client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        data = res.json()
        assert "refresh_token" in data

    def test_login_token_type_is_bearer(self, client, registered_user):
        res = client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert res.json()["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client, registered_user):
        res = client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": "WrongPassword!",
        })
        assert res.status_code == 401

    def test_login_nonexistent_email_returns_401(self, client):
        res = client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "Password123!",
        })
        assert res.status_code == 401

    def test_login_deactivated_user_returns_403(self, client, db_session, db_engine):
        # Register then deactivate
        email = "deactivated@example.com"
        client.post("/api/v1/auth/register", json={
            "email": email, "password": "Password123!",
        })
        # Deactivate via DB
        SessionFactory = sessionmaker(bind=db_engine)
        with SessionFactory() as s:
            u = s.query(User).filter_by(email=email).first()
            if u:
                u.is_active = False
                s.commit()
        res = client.post("/api/v1/auth/login", json={
            "email": email, "password": "Password123!",
        })
        assert res.status_code in (401, 403)


# ===========================================================================
# Refresh Token Tests
# ===========================================================================

class TestRefreshToken:

    def test_refresh_returns_new_access_token(self, client, registered_user):
        login = client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        refresh = login.json()["refresh_token"]
        res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_refresh_rotates_refresh_token(self, client, registered_user):
        login = client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        old_refresh = login.json()["refresh_token"]
        res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert res.json()["refresh_token"] != old_refresh

    def test_refresh_with_invalid_token_returns_401(self, client):
        res = client.post("/api/v1/auth/refresh", json={"refresh_token": "not.a.valid.jwt.token"})
        assert res.status_code == 401

    def test_refresh_with_short_token_returns_422(self, client):
        res = client.post("/api/v1/auth/refresh", json={"refresh_token": "short"})
        assert res.status_code == 422

    def test_reuse_rotated_refresh_token_returns_401(self, client, registered_user):
        login = client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        old_refresh = login.json()["refresh_token"]
        client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        # Second use must fail
        res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert res.status_code == 401


# ===========================================================================
# Logout Tests
# ===========================================================================

class TestLogout:

    def test_logout_returns_success(self, client, registered_user):
        login = client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        refresh = login.json()["refresh_token"]
        res = client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
        assert res.status_code == 200
        assert res.json()["status"] == "success"

    def test_logout_without_body_returns_200(self, client):
        res = client.post("/api/v1/auth/logout")
        assert res.status_code == 200

    def test_logout_with_bearer_header(self, client, registered_user):
        login = client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        access = login.json()["access_token"]
        res = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access}"},
        )
        assert res.status_code == 200
        assert res.json()["revoked"] is True


# ===========================================================================
# Profile Endpoint Tests
# ===========================================================================

class TestProfile:

    def _login(self, client, email, password):
        return client.post("/api/v1/auth/login", json={"email": email, "password": password}).json()

    def test_get_profile_with_valid_token_returns_200(self, client, registered_user):
        tokens = self._login(client, registered_user["email"], registered_user["password"])
        res = client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert res.status_code == 200

    def test_get_profile_returns_correct_email(self, client, registered_user):
        tokens = self._login(client, registered_user["email"], registered_user["password"])
        data = client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        ).json()
        assert data["email"] == registered_user["email"]

    def test_get_profile_without_token_returns_401(self, client):
        res = client.get("/api/v1/auth/profile")
        assert res.status_code == 401

    def test_get_profile_with_invalid_token_returns_401(self, client):
        res = client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert res.status_code == 401

    def test_get_me_alias_matches_profile(self, client, registered_user):
        tokens = self._login(client, registered_user["email"], registered_user["password"])
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        profile = client.get("/api/v1/auth/profile", headers=headers).json()
        me = client.get("/api/v1/auth/me", headers=headers).json()
        assert profile["email"] == me["email"]
        assert profile["id"] == me["id"]
