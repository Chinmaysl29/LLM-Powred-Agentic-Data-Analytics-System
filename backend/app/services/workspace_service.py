"""Workspace business service managing workspace lifecycle, scoping, and validation."""

from __future__ import annotations

import logging
import re
from typing import Any
import uuid

from backend.app.models.workspace import Workspace
from backend.app.repositories.workspace_repository import WorkspaceRepository

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Domain Exceptions
# ----------------------------------------------------------------------

class WorkspaceException(Exception):
    """Base exception for workspace domain errors."""
    pass


class WorkspaceNotFoundException(WorkspaceException):
    """Raised when a requested workspace does not exist."""
    pass


class DuplicateWorkspaceException(WorkspaceException):
    """Raised when a workspace slug already exists within the tenant."""
    pass


class WorkspaceValidationException(WorkspaceException):
    """Raised when input parameters fail workspace validation rules."""
    pass


# ----------------------------------------------------------------------
# Workspace Business Service
# ----------------------------------------------------------------------

class WorkspaceService:
    """Service handling workspace business rules, unique slug derivation, and lifecycle."""

    def __init__(self, repository: WorkspaceRepository) -> None:
        self.repository = repository

    @staticmethod
    def generate_slug(name: str) -> str:
        """Derive a URL-friendly slug from a workspace name."""
        if not name or not name.strip():
            raise WorkspaceValidationException("Cannot generate slug from empty workspace name")
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not slug:
            slug = f"ws-{uuid.uuid4().hex[:8]}"
        return slug

    def validate_workspace_data(self, name: str, slug: str | None = None) -> str:
        """Validate workspace display name and slug format."""
        clean_name = name.strip()
        if len(clean_name) < 2:
            raise WorkspaceValidationException("Workspace name must be at least 2 characters long")
        if len(clean_name) > 255:
            raise WorkspaceValidationException("Workspace name cannot exceed 255 characters")

        final_slug = (slug or self.generate_slug(clean_name)).strip().lower()
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", final_slug):
            raise WorkspaceValidationException(
                f"Invalid workspace slug '{final_slug}': must be lowercase alphanumeric with single hyphens"
            )
        if len(final_slug) > 100:
            raise WorkspaceValidationException("Workspace slug cannot exceed 100 characters")

        return final_slug

    def create_workspace(
        self,
        tenant_id: uuid.UUID | str,
        workspace_name: str,
        workspace_slug: str | None = None,
        description: str = "",
        status: str = "active",
    ) -> Workspace:
        """Create a new workspace within a tenant, enforcing per-tenant slug uniqueness."""
        parsed_tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        resolved_slug = self.validate_workspace_data(workspace_name, workspace_slug)

        existing = self.repository.get_by_slug(parsed_tid, resolved_slug)
        if existing:
            logger.warning("Duplicate workspace slug '%s' for tenant '%s'", resolved_slug, tenant_id)
            raise DuplicateWorkspaceException(
                f"Workspace with slug '{resolved_slug}' already exists in this tenant"
            )

        ws = Workspace(
            tenant_id=parsed_tid,
            workspace_name=workspace_name.strip(),
            workspace_slug=resolved_slug,
            description=description.strip(),
            status=status,
        )
        created = self.repository.create_workspace(ws)
        logger.info("Created workspace id=%s slug=%s tenant_id=%s", created.id, created.workspace_slug, tenant_id)
        return created

    def get_workspace(self, workspace_id: uuid.UUID | str) -> Workspace:
        """Retrieve a workspace or raise WorkspaceNotFoundException."""
        ws = self.repository.get_workspace(workspace_id)
        if not ws:
            raise WorkspaceNotFoundException(f"Workspace '{workspace_id}' not found")
        return ws

    def get_by_slug(self, tenant_id: uuid.UUID | str, slug: str) -> Workspace:
        """Retrieve a workspace by slug within a tenant."""
        ws = self.repository.get_by_slug(tenant_id, slug)
        if not ws:
            raise WorkspaceNotFoundException(f"Workspace with slug '{slug}' not found in tenant '{tenant_id}'")
        return ws

    def list_workspaces(
        self,
        tenant_id: uuid.UUID | str,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
    ) -> list[Workspace]:
        """List workspaces belonging to a tenant."""
        return self.repository.list_workspaces(tenant_id=tenant_id, skip=skip, limit=limit, status=status)

    def activate_workspace(self, workspace_id: uuid.UUID | str) -> Workspace:
        """Activate a suspended or new workspace."""
        ws = self.get_workspace(workspace_id)
        updated = self.repository.update_workspace(ws.id, status="active")
        if not updated:
            raise WorkspaceNotFoundException(f"Workspace '{workspace_id}' not found")
        logger.info("Activated workspace id=%s", updated.id)
        return updated

    def suspend_workspace(self, workspace_id: uuid.UUID | str, reason: str = "") -> Workspace:
        """Suspend a workspace, temporarily locking out edits."""
        ws = self.get_workspace(workspace_id)
        updated = self.repository.update_workspace(ws.id, status="suspended")
        if not updated:
            raise WorkspaceNotFoundException(f"Workspace '{workspace_id}' not found")
        logger.warning("Suspended workspace id=%s reason=%s", updated.id, reason)
        return updated

    def archive_workspace(self, workspace_id: uuid.UUID | str) -> Workspace:
        """Archive a decommissioned workspace."""
        ws = self.get_workspace(workspace_id)
        updated = self.repository.update_workspace(ws.id, status="archived")
        if not updated:
            raise WorkspaceNotFoundException(f"Workspace '{workspace_id}' not found")
        logger.info("Archived workspace id=%s", updated.id)
        return updated
