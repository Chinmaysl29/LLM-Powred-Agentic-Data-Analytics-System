"""Unit & Integration Tests for Phase 10.6: Production Security.

Validates:
- SSL/TLS & HSTS security headers
- Test Case: Unauthorized Request -> Expected: Blocked (401 / 403)
- Rate limiting quota breach -> Expected: Blocked (429)
- Active blocking of SQL injection and prompt injection attack vectors
- Overall 100% SECURE audit outcome
"""

import pytest
from backend.deployment.production_security_audit import ProductionSecurityAudit, production_security_audit
from backend.security.auth_service import auth_service


@pytest.fixture
def sec_audit():
    return ProductionSecurityAudit()


def test_security_headers_compliance(sec_audit):
    """Verify HSTS, no-sniff, and deny-frame headers are properly configured."""
    res = sec_audit.audit_security_headers()
    assert res["status"] == "PASS"
    assert res["hsts_active"] is True
    assert res["nosniff_active"] is True
    assert res["xframe_deny_active"] is True


def test_unauthorized_missing_token_blocked(sec_audit):
    """Test Case: Unauthorized Request (no token) -> Expected: Blocked (401)."""
    res = sec_audit.evaluate_unauthorized_request(token=None, required_permission="run_forecast")
    assert res["status"] == "BLOCKED"
    assert res["blocked"] is True
    assert res["status_code"] == 401


def test_unauthorized_viewer_cannot_admin(sec_audit):
    """Test Case: Unauthorized Request (viewer accessing admin action) -> Expected: Blocked (403)."""
    # Issue a valid token for viewer role
    tokens = auth_service.create_token_pair("test_v1", "viewer@test.com", "viewer")
    res = sec_audit.evaluate_unauthorized_request(
        token=tokens["access_token"],
        role="viewer",
        required_permission="manage_users",
    )
    assert res["status"] == "BLOCKED"
    assert res["blocked"] is True
    assert res["status_code"] == 403


def test_rate_limiting_breach_blocked(sec_audit):
    """Verify exceeding rate limit triggers 429 and blocks traffic."""
    res = sec_audit.audit_rate_limiting(requests_in_minute=130, limit=120)
    assert res["status"] == "PASS"
    assert res["blocked"] is True
    assert res["status_code"] == 429


def test_full_production_security_audit_secure(sec_audit):
    """Verify comprehensive production security audit passes with 100% score."""
    report = sec_audit.run_full_security_audit()
    assert report["overall_status"] == "SECURE"
    assert report["security_score"] == 100.0
    for check_name, check_status in report["checks"].items():
        assert check_status in {"PASS", "BLOCKED"}
