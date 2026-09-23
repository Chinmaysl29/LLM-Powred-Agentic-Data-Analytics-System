"""Workspace repository providing database CRUD operations for the Workspace model."""

from __future__ import annotations

import logging
from typing import Any
import uuid

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db_session
from backend.app.models.workspace import Workspace

logger = logging.getLogger(__name__)


class WorkspaceRepository:
    """Repository managing persistence and retrieval of Workspace entities."""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        # Fallback memory store when running without an active DB connection
        self._memory_store: dict[uuid.UUID, Workspace] = {}

    @property
    def session(self) -> Session | None:
        """Backward-compatible alias for the database session."""
        return self.db

    def create_workspace(self, workspace: Workspace) -> Workspace:
        """Persist a new Workspace record."""
        from datetime import datetime, timezone
        if not workspace.id:
            workspace.id = uuid.uuid4()
        if not getattr(workspace, "created_at", None):
            workspace.created_at = datetime.now(timezone.utc)
        if not getattr(workspace, "updated_at", None):
            workspace.updated_at = datetime.now(timezone.utc)
        if self.db is not None:
            self.db.add(workspace)
            self.db.commit()
            self.db.refresh(workspace)
        else:
            self._memory_store[workspace.id] = workspace

        logger.info(
            "Created workspace id=%s tenant_id=%s slug=%s name=%s",
            workspace.id,
            workspace.tenant_id,
            workspace.workspace_slug,
            workspace.workspace_name,
        )
        return workspace

    def get_workspace(self, workspace_id: uuid.UUID | str) -> Workspace | None:
        """Retrieve a Workspace by its unique UUID."""
        parsed_id = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        if self.db is not None:
            stmt = select(Workspace).where(Workspace.id == parsed_id)
            ws = self.db.scalars(stmt).first()
        else:
            ws = self._memory_store.get(parsed_id)

        if ws:
            logger.debug("Retrieved workspace id=%s", workspace_id)
        else:
            logger.warning("Workspace not found id=%s", workspace_id)
        return ws

    def get_by_slug(self, tenant_id: uuid.UUID | str, slug: str) -> Workspace | None:
        """Retrieve a Workspace by slug within a specific tenant."""
        parsed_tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        normalized_slug = slug.strip().lower()
        if self.db is not None:
            stmt = select(Workspace).where(
                Workspace.tenant_id == parsed_tid,
                Workspace.workspace_slug == normalized_slug,
            )
            ws = self.db.scalars(stmt).first()
        else:
            ws = next(
                (w for w in self._memory_store.values() if w.tenant_id == parsed_tid and w.workspace_slug == normalized_slug),
                None,
            )

        if ws:
            logger.debug("Retrieved workspace by tenant=%s slug=%s", tenant_id, normalized_slug)
        else:
            logger.warning("Workspace not found for tenant=%s slug=%s", tenant_id, normalized_slug)
        return ws

    def list_workspaces(
        self,
        tenant_id: uuid.UUID | str,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
    ) -> list[Workspace]:
        """List all workspaces belonging to a tenant."""
        parsed_tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        if self.db is not None:
            stmt = select(Workspace).where(Workspace.tenant_id == parsed_tid).order_by(Workspace.created_at.desc())
            if status:
                stmt = stmt.where(Workspace.status == status)
            stmt = stmt.offset(skip).limit(limit)
            results = list(self.db.scalars(stmt).all())
        else:
            results = [w for w in self._memory_store.values() if w.tenant_id == parsed_tid]
            if status:
                results = [w for w in results if w.status == status]
            results = results[skip : skip + limit]

        logger.debug("Listed workspaces count=%d for tenant_id=%s", len(results), tenant_id)
        return results

    def update_workspace(
        self,
        workspace_id: uuid.UUID | str,
        **updates: Any,
    ) -> Workspace | None:
        """Update mutable fields of a Workspace."""
        ws = self.get_workspace(workspace_id)
        if not ws:
            return None

        allowed = {"workspace_name", "workspace_slug", "description", "status"}
        applied = {}
        for k, v in updates.items():
            if k in allowed and v is not None:
                setattr(ws, k, v)
                applied[k] = v

        if applied:
            if self.db is not None:
                self.db.commit()
                self.db.refresh(ws)
            logger.info("Updated workspace id=%s fields=%s", workspace_id, list(applied.keys()))

        return ws

    def delete_workspace(self, workspace_id: uuid.UUID | str) -> bool:
        """Delete a Workspace and cascade to dependent entities."""
        ws = self.get_workspace(workspace_id)
        if not ws:
            return False

        if self.db is not None:
            self.db.delete(ws)
            self.db.commit()
        else:
            self._memory_store.pop(ws.id, None)

        logger.info("Deleted workspace id=%s", workspace_id)
        return True


# Global fallback instance for dependency injection when DB session is not active
_GLOBAL_FALLBACK_REPO = WorkspaceRepository(db=None)


def get_workspace_repository(db: Session = Depends(get_db_session)) -> WorkspaceRepository:
    """FastAPI dependency yielding a WorkspaceRepository instance."""
    if db is not None:
        return WorkspaceRepository(db=db)
    return _GLOBAL_FALLBACK_REPO
