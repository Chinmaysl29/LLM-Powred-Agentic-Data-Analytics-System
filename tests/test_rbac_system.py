"""Tests for Phase 8.2: Role-Based Access Control (RBAC)."""

import pytest
from fastapi import HTTPException

from backend.security.rbac import (
    Role,
    enforce_permission,
    get_user_permissions,
    has_permission,
    require_permission,
)


class MockUser:
    def __init__(self, role: str, email: str = "test@example.com"):
        self.role = role
        self.email = email


def test_get_user_permissions_analyst():
    """Verify analyst role permissions output structure."""
    result = get_user_permissions("analyst")
    assert result["role"] == "analyst"
    assert isinstance(result["permissions"], list)
    assert "run_forecast" in result["permissions"]
    assert "view_reports" in result["permissions"]
    assert "generate_recommendations" in result["permissions"]
    assert "manage_users" not in result["permissions"]


def test_viewer_attempting_admin_api_forbidden():
    """Test Case: Viewer attempting Admin API -> 403 Forbidden."""
    viewer_user = MockUser(role="viewer", email="viewer@enterprise.com")

    # Viewer can read reports
    assert has_permission(viewer_user.role, "view_reports") is True

    # Viewer cannot manage users or delete datasets
    assert has_permission(viewer_user.role, "manage_users") is False
    assert has_permission(viewer_user.role, "delete_any_dataset") is False

    # Enforcement must raise 403
    with pytest.raises(HTTPException) as exc_info:
        enforce_permission(viewer_user.role, "manage_users")

    assert exc_info.value.status_code == 403
    assert "manage_users" in exc_info.value.detail


def test_all_five_roles_exist():
    """Ensure Admin, Analyst, Manager, Executive, Viewer are supported."""
    roles = [r.value for r in Role]
    for expected in ["admin", "analyst", "manager", "executive", "viewer"]:
        assert expected in roles
        perms = get_user_permissions(expected)
        assert perms["role"] == expected
        assert len(perms["permissions"]) > 0


def test_manager_and_executive_approvals():
    """Test that managers and executives can approve recommendations."""
    assert has_permission("manager", "approve_recommendations") is True
    assert has_permission("executive", "approve_recommendations") is True
    assert has_permission("analyst", "approve_recommendations") is False
    assert has_permission("viewer", "approve_recommendations") is False


def test_require_permission_dependency():
    """Test FastAPI dependency checker."""
    admin_user = MockUser(role="admin")
    viewer_user = MockUser(role="viewer")

    admin_checker = require_permission("manage_settings")
    # Admin passes
    assert admin_checker(admin_user) == admin_user

    # Viewer raises 403
    with pytest.raises(HTTPException) as exc_info:
        admin_checker(viewer_user)
    assert exc_info.value.status_code == 403
