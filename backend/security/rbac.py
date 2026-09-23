"""Role-based access control (RBAC) for Phase 8 Enterprise Platform.

Roles:
- Admin
- Analyst
- Manager
- Executive
- Viewer

Permissions cover:
- datasets
- reports
- dashboards
- forecasts
- recommendations
- enterprise administration
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Callable

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """Enterprise platform roles."""

    ADMIN = "admin"
    ANALYST = "analyst"
    MANAGER = "manager"
    EXECUTIVE = "executive"
    VIEWER = "viewer"


# Comprehensive permission matrix across:
# datasets, reports, dashboards, forecasts, recommendations, administration
ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.VIEWER.value: {
        "read_dataset",
        "view_datasets",
        "read_report",
        "view_reports",
        "download_reports",
        "read_dashboard",
        "view_dashboards",
        "read_analysis",
        "view_forecasts",
        "view_recommendations",
    },
    Role.ANALYST.value: {
        # Datasets
        "read_dataset",
        "view_datasets",
        "write_dataset",
        "upload_dataset",
        "create_datasets",
        "delete_own_dataset",
        # Reports
        "read_report",
        "view_reports",
        "create_reports",
        "create_report",
        "download_reports",
        # Dashboards
        "read_dashboard",
        "view_dashboards",
        "create_dashboards",
        "create_dashboard",
        "edit_dashboards",
        # Forecasts
        "view_forecasts",
        "run_forecast",
        "use_forecast",
        # Recommendations
        "view_recommendations",
        "generate_recommendations",
        "use_recommendations",
        # Analysis
        "read_analysis",
        "create_analysis",
        "run_query",
        "use_chat",
    },
    Role.MANAGER.value: {
        # Inherits Analyst + approval/oversight
        "read_dataset",
        "view_datasets",
        "write_dataset",
        "upload_dataset",
        "create_datasets",
        "delete_own_dataset",
        "read_report",
        "view_reports",
        "create_reports",
        "create_report",
        "download_reports",
        "read_dashboard",
        "view_dashboards",
        "create_dashboards",
        "create_dashboard",
        "edit_dashboards",
        "view_forecasts",
        "run_forecast",
        "use_forecast",
        "view_recommendations",
        "generate_recommendations",
        "approve_recommendations",
        "use_recommendations",
        "read_analysis",
        "create_analysis",
        "run_query",
        "use_chat",
        "view_audit_logs",
    },
    Role.EXECUTIVE.value: {
        # High-level strategic oversight
        "read_dataset",
        "view_datasets",
        "read_report",
        "view_reports",
        "create_reports",
        "create_report",
        "download_reports",
        "read_dashboard",
        "view_dashboards",
        "create_dashboards",
        "create_dashboard",
        "view_forecasts",
        "run_forecast",
        "view_recommendations",
        "approve_recommendations",
        "view_audit_logs",
        "read_analysis",
        "use_chat",
    },
    Role.ADMIN.value: {
        # Full administrative superuser privileges
        "read_dataset",
        "view_datasets",
        "write_dataset",
        "upload_dataset",
        "create_datasets",
        "delete_own_dataset",
        "delete_any_dataset",
        "read_report",
        "view_reports",
        "create_reports",
        "create_report",
        "download_reports",
        "delete_report",
        "read_dashboard",
        "view_dashboards",
        "create_dashboards",
        "create_dashboard",
        "edit_dashboards",
        "delete_dashboard",
        "view_forecasts",
        "run_forecast",
        "use_forecast",
        "view_recommendations",
        "generate_recommendations",
        "approve_recommendations",
        "use_recommendations",
        "read_analysis",
        "create_analysis",
        "delete_analysis",
        "run_query",
        "use_chat",
        "manage_users",
        "view_audit_logs",
        "manage_settings",
        "system_admin",
    },
}


def normalize_role(role: str) -> str:
    """Normalize role string to lowercase standard enum value."""
    clean = str(role).strip().lower()
    if clean in {r.value for r in Role}:
        return clean
    # Fallback to viewer if unrecognized
    return Role.VIEWER.value


def get_user_permissions(role: str) -> dict[str, Any]:
    """Return dictionary of role and sorted permissions list."""
    norm_role = normalize_role(role)
    perms = sorted(list(ROLE_PERMISSIONS.get(norm_role, set())))
    return {
        "role": norm_role,
        "permissions": perms,
    }


def has_permission(user_role: str, permission: str) -> bool:
    """Check if a role possesses the requested permission."""
    norm_role = normalize_role(user_role)
    if norm_role == Role.ADMIN.value:
        return True
    perms = ROLE_PERMISSIONS.get(norm_role, set())
    if permission in perms:
        return True
    if permission == "read" and any(p.startswith("read_") or p.startswith("view_") for p in perms):
        return True
    if permission == "write" and any(p.startswith("write_") or p.startswith("create_") or p.startswith("upload_") for p in perms):
        return True
    if permission == "delete" and any(p.startswith("delete_") for p in perms):
        return True
    return False


def enforce_permission(user_role: str, permission: str) -> None:
    """Raise HTTP 403 Forbidden if user lacks required permission."""
    if not has_permission(user_role, permission):
        logger.warning(
            "Access denied: role '%s' lacks required permission '%s'",
            user_role,
            permission,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: '{permission}' required for role '{user_role}'",
        )


def require_permission(permission: str) -> Callable:
    """FastAPI dependency checking if current user has permission."""

    def checker(current_user: Any) -> Any:
        role = getattr(current_user, "role", "viewer")
        enforce_permission(role, permission)
        return current_user

    return checker
