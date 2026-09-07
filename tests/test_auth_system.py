"""Tests for Phase 8.1: Authentication System."""

import pytest
from backend.security.auth_service import AuthService
from backend.app.schemas.auth import AuthResponse, RefreshTokenRequest, LogoutRequest, LoginRequest


@pytest.fixture
def auth_service():
    return AuthService()


def test_create_token_pair(auth_service):
    """Verify that token generation produces access_token, refresh_token, and expires_in."""
    res = auth_service.create_token_pair(
        user_id="user-123",
        email="analyst@enterprise.com",
        role="analyst",
    )
    assert "access_token" in res
    assert "refresh_token" in res
    assert res["expires_in"] == 3600
    assert res["token_type"] == "bearer"

    # Verify access token
    payload = auth_service.verify_token(res["access_token"])
    assert payload["sub"] == "user-123"
    assert payload["email"] == "analyst@enterprise.com"
    assert payload["role"] == "analyst"
    assert payload["token_type"] == "access"


def test_session_validation(auth_service):
    """Test session validation of an active token."""
    res = auth_service.create_token_pair("user-456", "admin@enterprise.com", "admin")
    session = auth_service.validate_session(res["access_token"])
    assert session["valid"] is True
    assert session["user_id"] == "user-456"
    assert session["role"] == "admin"


def test_refresh_token_rotation(auth_service):
    """Verify single-use refresh token rotation."""
    res = auth_service.create_token_pair("user-789", "mgr@enterprise.com", "manager")
    old_refresh = res["refresh_token"]

    # Rotate refresh token
    new_res = auth_service.refresh_token(old_refresh)
    assert "access_token" in new_res
    assert "refresh_token" in new_res
    assert new_res["refresh_token"] != old_refresh

    # Old refresh token should now be revoked
    with pytest.raises(ValueError, match="revoked"):
        auth_service.refresh_token(old_refresh)


def test_token_revocation_and_logout(auth_service):
    """Verify token revocation invalidates the token."""
    res = auth_service.create_token_pair("user-999", "exec@enterprise.com", "executive")
    token = res["access_token"]

    # Initially valid
    assert auth_service.verify_token(token)["sub"] == "user-999"

    # Revoke
    auth_service.revoke_token(token)

    # Now invalid
    with pytest.raises(ValueError, match="revoked"):
        auth_service.verify_token(token)


def test_auth_response_schema():
    """Verify schema matches enterprise output requirements."""
    resp = AuthResponse(
        access_token="acc-token-xyz",
        refresh_token="ref-token-abc",
        expires_in=3600,
    )
    assert resp.access_token == "acc-token-xyz"
    assert resp.refresh_token == "ref-token-abc"
    assert resp.expires_in == 3600
    assert resp.token_type == "bearer"
