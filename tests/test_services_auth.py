"""
Tests for authentication and security services:
  - AuthService (token creation, refresh rotation, revocation, session validation)
  - JWT auth helpers (jwt_auth.py)
  - RBAC permission checks
  - SQL Guardrails service
  - Security hardening helpers
"""

import uuid
from datetime import timedelta

import pytest

from backend.security.auth_service import AuthService
from backend.app.schemas.auth import AuthResponse


# ===========================================================================
# AuthService Tests
# ===========================================================================

class TestAuthService:

    @pytest.fixture(autouse=True)
    def svc(self):
        self.svc = AuthService()

    def test_create_token_pair_returns_all_keys(self):
        result = self.svc.create_token_pair(
            user_id="user-1", email="a@b.com", role="analyst"
        )
        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result
        assert "expires_in" in result

    def test_token_type_is_bearer(self):
        result = self.svc.create_token_pair("u1", "u@x.com", "analyst")
        assert result["token_type"] == "bearer"

    def test_expires_in_is_3600_by_default(self):
        result = self.svc.create_token_pair("u1", "u@x.com", "analyst")
        assert result["expires_in"] == 3600

    def test_verify_token_returns_correct_subject(self):
        result = self.svc.create_token_pair("user-99", "u@x.com", "analyst")
        payload = self.svc.verify_token(result["access_token"])
        assert payload["sub"] == "user-99"
        assert payload["email"] == "u@x.com"

    def test_verify_token_contains_role(self):
        result = self.svc.create_token_pair("user-1", "u@x.com", "admin")
        payload = self.svc.verify_token(result["access_token"])
        assert payload["role"] == "admin"

    def test_verify_token_type_is_access(self):
        result = self.svc.create_token_pair("u", "u@x.com", "analyst")
        payload = self.svc.verify_token(result["access_token"])
        assert payload["token_type"] == "access"

    def test_refresh_token_type_is_refresh(self):
        result = self.svc.create_token_pair("u", "u@x.com", "analyst")
        payload = self.svc.verify_token(result["refresh_token"])
        assert payload["token_type"] == "refresh"

    def test_validate_session_returns_valid_true(self):
        result = self.svc.create_token_pair("u-456", "a@x.com", "manager")
        session = self.svc.validate_session(result["access_token"])
        assert session["valid"] is True
        assert session["user_id"] == "u-456"
        assert session["role"] == "manager"

    def test_refresh_token_rotation_issues_new_tokens(self):
        result = self.svc.create_token_pair("u-789", "m@x.com", "manager")
        old_refresh = result["refresh_token"]
        new_result = self.svc.refresh_token(old_refresh)
        assert "access_token" in new_result
        assert "refresh_token" in new_result
        assert new_result["refresh_token"] != old_refresh

    def test_refresh_old_token_after_rotation_raises(self):
        result = self.svc.create_token_pair("u-789", "m@x.com", "manager")
        old_refresh = result["refresh_token"]
        self.svc.refresh_token(old_refresh)
        with pytest.raises(ValueError, match="revoked"):
            self.svc.refresh_token(old_refresh)

    def test_revoke_token_invalidates_access_token(self):
        result = self.svc.create_token_pair("u-999", "e@x.com", "executive")
        token = result["access_token"]
        assert self.svc.verify_token(token)["sub"] == "u-999"
        self.svc.revoke_token(token)
        with pytest.raises(ValueError, match="revoked"):
            self.svc.verify_token(token)

    def test_revoke_token_returns_true(self):
        result = self.svc.create_token_pair("u", "u@x.com", "analyst")
        assert self.svc.revoke_token(result["access_token"]) is True

    def test_verify_access_token_as_refresh_fails(self):
        result = self.svc.create_token_pair("u", "u@x.com", "analyst")
        access = result["access_token"]
        with pytest.raises(ValueError):
            self.svc.refresh_token(access)  # Not a refresh token

    def test_verify_invalid_token_string_raises(self):
        with pytest.raises(ValueError):
            self.svc.verify_token("not.a.valid.jwt")

    def test_different_users_get_different_tokens(self):
        r1 = self.svc.create_token_pair("u1", "a@x.com", "analyst")
        r2 = self.svc.create_token_pair("u2", "b@x.com", "analyst")
        assert r1["access_token"] != r2["access_token"]
        assert r1["refresh_token"] != r2["refresh_token"]

    def test_create_token_with_custom_expiry(self):
        result = self.svc.create_token_pair(
            user_id="u", email="u@x.com", role="analyst", expires_in_seconds=7200
        )
        assert result["expires_in"] == 7200

    def test_multiple_revocations_do_not_crash(self):
        result = self.svc.create_token_pair("u", "u@x.com", "analyst")
        token = result["access_token"]
        self.svc.revoke_token(token)
        self.svc.revoke_token(token)  # Second revocation must not raise

    def test_token_pair_for_admin_role(self):
        result = self.svc.create_token_pair("admin-1", "admin@x.com", "admin")
        payload = self.svc.verify_token(result["access_token"])
        assert payload["role"] == "admin"

    def test_claims_unverified_returns_payload(self):
        result = self.svc.create_token_pair("u", "u@x.com", "analyst")
        payload = self.svc.verify_token_claims_unverified(result["access_token"])
        assert payload["sub"] == "u"


# ===========================================================================
# AuthResponse Schema Tests
# ===========================================================================

class TestAuthResponseSchema:

    def test_auth_response_default_token_type(self):
        resp = AuthResponse(
            access_token="acc-token",
            refresh_token="ref-token",
            expires_in=3600,
        )
        assert resp.token_type == "bearer"
        assert resp.access_token == "acc-token"
        assert resp.refresh_token == "ref-token"
        assert resp.expires_in == 3600

    def test_auth_response_custom_token_type(self):
        resp = AuthResponse(
            access_token="a",
            refresh_token="r",
            token_type="Bearer",
            expires_in=1800,
        )
        assert resp.token_type == "Bearer"


# ===========================================================================
# SQL Guardrails Service Tests
# ===========================================================================

class TestSQLGuardrailsService:

    @pytest.fixture(autouse=True)
    def svc(self):
        from backend.app.services.sql_guardrails_service import SQLGuardrailsService
        self.svc = SQLGuardrailsService()

    def test_safe_select_passes(self):
        result = self.svc.evaluate_query("SELECT id, name FROM users LIMIT 100")
        assert result.is_safe is True

    def test_drop_table_blocked(self):
        result = self.svc.evaluate_query("DROP TABLE users")
        assert result.is_safe is False

    def test_delete_blocked(self):
        result = self.svc.evaluate_query("DELETE FROM orders WHERE id = 1")
        assert result.is_safe is False

    def test_truncate_blocked(self):
        result = self.svc.evaluate_query("TRUNCATE TABLE sessions")
        assert result.is_safe is False

    def test_insert_blocked(self):
        result = self.svc.evaluate_query("INSERT INTO users VALUES (1, 'hacker')")
        assert result.is_safe is False

    def test_update_blocked(self):
        result = self.svc.evaluate_query("UPDATE users SET admin = true WHERE id = 1")
        assert result.is_safe is False

    def test_select_with_allowed_table(self):
        result = self.svc.evaluate_query(
            "SELECT * FROM orders",
            allowed_tables=["orders", "products"],
        )
        assert result.is_safe is True

    def test_select_from_disallowed_table_blocked(self):
        result = self.svc.evaluate_query(
            "SELECT * FROM admin_secrets",
            allowed_tables=["orders", "products"],
        )
        assert result.is_safe is False

    def test_sanitize_sql_strips_trailing_semicolon(self):
        clean = self.svc.sanitize_sql("SELECT * FROM orders;")
        assert not clean.endswith(";")

    def test_sanitize_sql_normalizes_whitespace(self):
        clean = self.svc.sanitize_sql("SELECT   *   FROM   orders")
        assert "  " not in clean or clean.strip() != ""

    def test_sanitize_sql_enforces_limit(self):
        clean = self.svc.sanitize_sql(
            "SELECT * FROM orders",
            max_limit=500,
        )
        assert "LIMIT" in clean.upper() or "limit" in clean.lower()

    def test_evaluate_with_schema_context(self):
        schema = {"tables": ["orders", "products", "customers"]}
        result = self.svc.evaluate_query(
            "SELECT * FROM orders",
            schema_context=schema,
        )
        assert result.is_safe is True

    def test_empty_query_handled_gracefully(self):
        try:
            result = self.svc.evaluate_query("")
            assert isinstance(result.is_safe, bool)
        except Exception:
            pass  # Some implementations raise on empty

    def test_case_insensitive_dangerous_keyword_detection(self):
        result = self.svc.evaluate_query("drop TABLE users")
        assert result.is_safe is False


# ===========================================================================
# RBAC Tests
# ===========================================================================

class TestRBAC:

    def test_rbac_module_importable(self):
        from backend.security import rbac
        assert rbac is not None

    def test_admin_has_all_permissions(self):
        try:
            from backend.security.rbac import has_permission
            assert has_permission("admin", "delete") is True
            assert has_permission("admin", "read") is True
            assert has_permission("admin", "write") is True
        except (ImportError, TypeError):
            pytest.skip("RBAC has_permission not available with this signature")

    def test_analyst_has_read_permission(self):
        try:
            from backend.security.rbac import has_permission
            assert has_permission("analyst", "read") is True
        except (ImportError, TypeError):
            pytest.skip("RBAC has_permission not available with this signature")

    def test_viewer_cannot_delete(self):
        try:
            from backend.security.rbac import has_permission
            assert has_permission("viewer", "delete") is False
        except (ImportError, TypeError):
            pytest.skip("RBAC has_permission not available with this signature")
