"""REST API routes for Enterprise Workspace Management."""

from __future__ import annotations

import logging
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db_session
from backend.app.repositories.workspace_repository import WorkspaceRepository, get_workspace_repository
from backend.app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceListResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from backend.app.services.workspace_service import (
    DuplicateWorkspaceException,
    WorkspaceNotFoundException,
    WorkspaceService,
    WorkspaceValidationException,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["Enterprise Workspace Management"])


def get_workspace_service(
    repo: WorkspaceRepository = Depends(get_workspace_repository),
) -> WorkspaceService:
    """Dependency provider for WorkspaceService."""
    return WorkspaceService(repository=repo)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    service: WorkspaceService = Depends(get_workspace_service),
) -> Any:
    """Create a new workspace within an enterprise tenant."""
    try:
        return service.create_workspace(
            tenant_id=payload.tenant_id,
            workspace_name=payload.workspace_name,
            workspace_slug=payload.workspace_slug,
            description=payload.description or "",
            status=payload.status,
        )
    except DuplicateWorkspaceException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except WorkspaceValidationException as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("", response_model=WorkspaceListResponse)
def list_workspaces(
    tenant_id: uuid.UUID = Query(..., description="Parent tenant UUID to list workspaces for"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    status: str | None = Query(default=None),
    service: WorkspaceService = Depends(get_workspace_service),
) -> Any:
    """List all workspaces for a given tenant."""
    items = service.list_workspaces(tenant_id=tenant_id, skip=skip, limit=limit, status=status)
    return {
        "items": items,
        "total": len(items),
        "skip": skip,
        "limit": limit,
    }


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: uuid.UUID,
    service: WorkspaceService = Depends(get_workspace_service),
) -> Any:
    """Retrieve details of a single workspace by ID."""
    try:
        return service.get_workspace(workspace_id)
    except WorkspaceNotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    repo: WorkspaceRepository = Depends(get_workspace_repository),
) -> Any:
    """Update metadata or status of an existing workspace."""
    updated = repo.update_workspace(
        workspace_id=workspace_id,
        workspace_name=payload.workspace_name,
        description=payload.description,
        status=payload.status,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )
    return updated


@router.delete("/{workspace_id}", status_code=status.HTTP_200_OK)
def delete_workspace(
    workspace_id: uuid.UUID,
    repo: WorkspaceRepository = Depends(get_workspace_repository),
) -> dict[str, Any]:
    """Delete a workspace and all nested departmental/project assets."""
    deleted = repo.delete_workspace(workspace_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found",
        )
    return {"status": "success", "deleted_workspace_id": str(workspace_id)}
