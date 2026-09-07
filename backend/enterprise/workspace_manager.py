"""Phase 12.2 — Enterprise Workspace Management

Provides departmental and project-level workspace isolation within each tenant,
role-based membership management, and dataset/dashboard tenancy mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

from backend.enterprise.multi_tenant import TenantManager


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


ROLE_PERMISSIONS: Dict[WorkspaceRole, Set[str]] = {
    WorkspaceRole.OWNER: {"read", "write", "delete", "manage_members", "manage_settings", "manage_billing"},
    WorkspaceRole.ADMIN: {"read", "write", "delete", "manage_members", "manage_settings"},
    WorkspaceRole.EDITOR: {"read", "write"},
    WorkspaceRole.VIEWER: {"read"},
}


@dataclass
class WorkspaceMember:
    user_id: str
    email: str
    role: WorkspaceRole
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role.value,
            "joined_at": self.joined_at.isoformat(),
        }


@dataclass
class Workspace:
    id: str
    tenant_id: str
    name: str
    slug: str
    department: str
    description: str = ""
    members: Dict[str, WorkspaceMember] = field(default_factory=dict)
    dataset_ids: List[str] = field(default_factory=list)
    dashboard_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_default: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "slug": self.slug,
            "department": self.department,
            "description": self.description,
            "members": [m.to_dict() for m in self.members.values()],
            "member_count": len(self.members),
            "dataset_ids": self.dataset_ids,
            "dashboard_ids": self.dashboard_ids,
            "created_at": self.created_at.isoformat(),
            "is_default": self.is_default,
        }


class WorkspaceManager:
    """Manages workspace lifecycle, department scoping, and membership."""

    _instance: Optional[WorkspaceManager] = None

    def __new__(cls) -> WorkspaceManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._workspaces: Dict[str, Workspace] = {}
            cls._instance._tenant_manager = TenantManager()
            cls._instance._seed_default_workspace()
        return cls._instance

    def _seed_default_workspace(self) -> None:
        """Seed default general workspace for system tenant."""
        ws_id = "ws-system-default"
        ws = Workspace(
            id=ws_id,
            tenant_id="system",
            name="General Operations",
            slug="general-operations",
            department="Cross-Functional",
            description="Default workspace for platform-wide operations",
            is_default=True,
        )
        self._workspaces[ws_id] = ws

    def create_workspace(
        self,
        tenant_id: str,
        name: str,
        department: str,
        owner_id: str,
        owner_email: str = "owner@tenant.internal",
        description: str = "",
        slug: Optional[str] = None,
    ) -> Workspace:
        """Provision a new workspace within a tenant."""
        # Validate tenant exists
        tenant = self._tenant_manager.get_tenant(tenant_id)
        if not tenant:
            raise KeyError(f"Tenant {tenant_id} not found")

        # Check tenant workspace quota
        current_workspaces = len([w for w in self._workspaces.values() if w.tenant_id == tenant_id])
        if current_workspaces >= tenant.quota.max_workspaces:
            raise ValueError(
                f"Workspace limit reached for tenant {tenant_id}: max={tenant.quota.max_workspaces}"
            )

        ws_id = f"ws-{uuid.uuid4().hex[:12]}"
        normalized_slug = (slug or name.lower().replace(" ", "-")).strip()

        owner_member = WorkspaceMember(
            user_id=owner_id,
            email=owner_email,
            role=WorkspaceRole.OWNER,
        )

        workspace = Workspace(
            id=ws_id,
            tenant_id=tenant_id,
            name=name,
            slug=normalized_slug,
            department=department,
            description=description,
            members={owner_id: owner_member},
        )
        self._workspaces[ws_id] = workspace
        self._tenant_manager.record_usage(tenant_id, "workspaces", 1)
        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Retrieve workspace by ID."""
        return self._workspaces.get(workspace_id)

    def list_workspaces(
        self,
        tenant_id: str,
        department: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Workspace]:
        """List workspaces for a tenant, optionally filtered by department or user membership."""
        results = [w for w in self._workspaces.values() if w.tenant_id == tenant_id]
        if department:
            results = [w for w in results if w.department.lower() == department.lower()]
        if user_id:
            results = [w for w in results if user_id in w.members]
        return results

    def add_member(
        self,
        workspace_id: str,
        user_id: str,
        email: str,
        role: WorkspaceRole = WorkspaceRole.VIEWER,
    ) -> WorkspaceMember:
        """Add or update a member in the workspace."""
        ws = self.get_workspace(workspace_id)
        if not ws:
            raise KeyError(f"Workspace {workspace_id} not found")

        member = WorkspaceMember(user_id=user_id, email=email, role=role)
        ws.members[user_id] = member
        return member

    def remove_member(self, workspace_id: str, user_id: str) -> None:
        """Remove a member from the workspace."""
        ws = self.get_workspace(workspace_id)
        if not ws:
            raise KeyError(f"Workspace {workspace_id} not found")
        if user_id in ws.members:
            # Prevent removing the sole owner
            member = ws.members[user_id]
            if member.role == WorkspaceRole.OWNER:
                owners = [m for m in ws.members.values() if m.role == WorkspaceRole.OWNER]
                if len(owners) <= 1:
                    raise ValueError("Cannot remove the sole owner of a workspace")
            del ws.members[user_id]

    def check_permission(self, workspace_id: str, user_id: str, action: str) -> bool:
        """Check whether a user has permission to perform an action in a workspace."""
        ws = self.get_workspace(workspace_id)
        if not ws:
            return False
        member = ws.members.get(user_id)
        if not member:
            return False
        allowed_actions = ROLE_PERMISSIONS.get(member.role, set())
        return action in allowed_actions

    def attach_dataset(self, workspace_id: str, dataset_id: str) -> None:
        """Associate a dataset with the workspace."""
        ws = self.get_workspace(workspace_id)
        if not ws:
            raise KeyError(f"Workspace {workspace_id} not found")
        if dataset_id not in ws.dataset_ids:
            ws.dataset_ids.append(dataset_id)

    def attach_dashboard(self, workspace_id: str, dashboard_id: str) -> None:
        """Associate a dashboard with the workspace."""
        ws = self.get_workspace(workspace_id)
        if not ws:
            raise KeyError(f"Workspace {workspace_id} not found")
        if dashboard_id not in ws.dashboard_ids:
            ws.dashboard_ids.append(dashboard_id)

    def get_workspace_analytics(self, workspace_id: str) -> Dict[str, Any]:
        """Aggregate workspace metrics."""
        ws = self.get_workspace(workspace_id)
        if not ws:
            raise KeyError(f"Workspace {workspace_id} not found")

        role_distribution: Dict[str, int] = {}
        for member in ws.members.values():
            role_distribution[member.role.value] = role_distribution.get(member.role.value, 0) + 1

        return {
            "workspace_id": ws.id,
            "name": ws.name,
            "department": ws.department,
            "total_members": len(ws.members),
            "role_distribution": role_distribution,
            "total_datasets": len(ws.dataset_ids),
            "total_dashboards": len(ws.dashboard_ids),
        }

    def reset(self) -> None:
        """Reset workspace storage for testing."""
        self._workspaces.clear()
        self._seed_default_workspace()
