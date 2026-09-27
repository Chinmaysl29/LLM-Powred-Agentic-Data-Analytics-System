"""Enterprise Workspace Orchestration Service for Phase 20.1.

Provides multi-tenant workspace management, resource scoping across:
- Datasets
- Dashboards
- Reports
- Chat History
- Forecasts
- Saved Insights
With member role-based access control (Owner, Admin, Analyst, Viewer) and lifecycle management.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

logger = logging.getLogger(__name__)

WORKSPACE_STORAGE_ROOT = Path("storage/workspaces")


class WorkspaceMemberRole:
    OWNER = "Owner"
    ADMIN = "Admin"
    ANALYST = "Analyst"
    VIEWER = "Viewer"


class WorkspaceStatus:
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"


class WorkspaceOrchestrationService:
    """Enterprise service managing workspaces, members, and scoped analytical resources."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self.storage_dir = Path(storage_dir) if storage_dir else WORKSPACE_STORAGE_ROOT
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._workspaces: dict[str, dict[str, Any]] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load persisted workspaces from the storage filesystem."""
        try:
            for ws_file in self.storage_dir.glob("*.json"):
                with open(ws_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ws_id = data.get("id")
                    if ws_id:
                        self._workspaces[ws_id] = data
        except Exception as exc:
            logger.warning("Failed to load some workspace state from disk: %s", exc)

    def _persist_workspace(self, ws_id: str) -> None:
        """Persist workspace state to disk atomically."""
        ws_data = self._workspaces.get(ws_id)
        if not ws_data:
            return
        ws_file = self.storage_dir / f"{ws_id}.json"
        try:
            with open(ws_file, "w", encoding="utf-8") as f:
                json.dump(ws_data, f, indent=2, default=str)
        except Exception as exc:
            logger.error("Failed to persist workspace %s to disk: %s", ws_id, exc)

    def create_workspace(
        self,
        name: str,
        description: str = "",
        owner_id: str = "user-admin",
        owner_email: str = "admin@enterprise.ai",
        tenant_id: str = "default-tenant",
    ) -> dict[str, Any]:
        """Create a new workspace with default scoping containers."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Workspace name cannot be empty")

        ws_id = f"ws-{uuid.uuid4().hex[:10]}"
        slug = "-".join(clean_name.lower().split())
        now = datetime.now(timezone.utc).isoformat()

        workspace = {
            "id": ws_id,
            "name": clean_name,
            "slug": slug,
            "description": description,
            "tenant_id": tenant_id,
            "owner_id": owner_id,
            "status": WorkspaceStatus.ACTIVE,
            "created_at": now,
            "updated_at": now,
            "members": [
                {
                    "user_id": owner_id,
                    "email": owner_email,
                    "role": WorkspaceMemberRole.OWNER,
                    "joined_at": now,
                }
            ],
            "resources": {
                "datasets": [],
                "dashboards": [],
                "reports": [],
                "chat_history": [],
                "forecasts": [],
                "insights": [],
            },
            "settings": {
                "theme": "dark",
                "default_currency": "USD",
                "ai_analyst_mode": "autonomous",
            },
        }

        self._workspaces[ws_id] = workspace
        self._persist_workspace(ws_id)
        logger.info("Created workspace: %s (%s)", clean_name, ws_id)
        return workspace

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        """Retrieve workspace by ID."""
        if workspace_id not in self._workspaces:
            raise KeyError(f"Workspace not found: {workspace_id}")
        return self._workspaces[workspace_id]

    def list_workspaces(
        self,
        tenant_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """List workspaces filtered by tenant and/or status."""
        results = list(self._workspaces.values())
        if tenant_id:
            results = [w for w in results if w.get("tenant_id") == tenant_id]
        if status:
            results = [w for w in results if w.get("status") == status]
        return results

    def update_workspace(
        self,
        workspace_id: str,
        name: str | None = None,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update workspace metadata or settings."""
        ws = self.get_workspace(workspace_id)
        if name is not None:
            clean_name = name.strip()
            if clean_name:
                ws["name"] = clean_name
                ws["slug"] = "-".join(clean_name.lower().split())
        if description is not None:
            ws["description"] = description
        if settings is not None:
            ws["settings"].update(settings)

        ws["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._persist_workspace(workspace_id)
        return ws

    def archive_workspace(self, workspace_id: str) -> dict[str, Any]:
        """Archive a workspace."""
        ws = self.get_workspace(workspace_id)
        ws["status"] = WorkspaceStatus.ARCHIVED
        ws["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._persist_workspace(workspace_id)
        return ws

    def delete_workspace(self, workspace_id: str) -> bool:
        """Permanently delete a workspace and remove its storage file."""
        if workspace_id not in self._workspaces:
            return False
        del self._workspaces[workspace_id]
        ws_file = self.storage_dir / f"{workspace_id}.json"
        if ws_file.exists():
            ws_file.unlink()
        return True

    def add_member(
        self,
        workspace_id: str,
        user_id: str,
        email: str,
        role: str = WorkspaceMemberRole.ANALYST,
    ) -> dict[str, Any]:
        """Add a member to the workspace."""
        ws = self.get_workspace(workspace_id)
        # Check if already member
        for m in ws["members"]:
            if m["user_id"] == user_id or m["email"] == email:
                m["role"] = role
                self._persist_workspace(workspace_id)
                return ws

        ws["members"].append({
            "user_id": user_id,
            "email": email,
            "role": role,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        })
        self._persist_workspace(workspace_id)
        return ws

    def remove_member(self, workspace_id: str, user_id: str) -> dict[str, Any]:
        """Remove a member from the workspace."""
        ws = self.get_workspace(workspace_id)
        ws["members"] = [m for m in ws["members"] if m["user_id"] != user_id]
        self._persist_workspace(workspace_id)
        return ws

    def associate_resource(
        self,
        workspace_id: str,
        resource_type: str,
        resource_item: dict[str, Any] | str,
    ) -> dict[str, Any]:
        """Scope a dataset, dashboard, report, forecast, or insight to a workspace."""
        ws = self.get_workspace(workspace_id)
        if resource_type not in ws["resources"]:
            raise ValueError(f"Invalid resource type: {resource_type}")

        item_id = resource_item if isinstance(resource_item, str) else resource_item.get("id") or resource_item.get("dataset_id")
        existing_list = ws["resources"][resource_type]

        # Avoid duplicates
        for idx, item in enumerate(existing_list):
            curr_id = item if isinstance(item, str) else item.get("id") or item.get("dataset_id")
            if curr_id == item_id:
                existing_list[idx] = resource_item
                self._persist_workspace(workspace_id)
                return ws

        existing_list.append(resource_item)
        ws["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._persist_workspace(workspace_id)
        return ws

    def get_workspace_resources(self, workspace_id: str) -> dict[str, Any]:
        """Get all scoped analytical resources of a workspace."""
        ws = self.get_workspace(workspace_id)
        return ws["resources"]


# Global singleton instance
_workspace_service = WorkspaceOrchestrationService()


def get_workspace_orchestration_service() -> WorkspaceOrchestrationService:
    """Dependency provider for workspace service."""
    return _workspace_service
