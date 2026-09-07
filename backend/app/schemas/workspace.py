"""Workspace Pydantic schemas for request validation and API serialization."""

from __future__ import annotations

from datetime import datetime
import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkspaceBase(BaseModel):
    """Base fields for workspaces."""

    workspace_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Official human-readable name of the workspace",
        examples=["Marketing Analytics"],
    )
    description: str | None = Field(
        default="",
        max_length=1000,
        description="Charter or description of the workspace",
    )


class WorkspaceCreate(WorkspaceBase):
    """Payload for creating a new workspace within a tenant."""

    tenant_id: uuid.UUID = Field(
        ...,
        description="Tenant organization owning this workspace",
    )
    workspace_slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Optional URL slug; auto-derived from workspace_name if omitted",
        examples=["marketing-analytics"],
    )
    status: str = Field(
        default="active",
        description="Initial lifecycle status",
    )

    @field_validator("workspace_slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        if value is not None:
            normalized = value.strip().lower()
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", normalized):
                raise ValueError(
                    "workspace_slug must be lowercase alphanumeric characters separated by single hyphens"
                )
            return normalized
        return value


class WorkspaceUpdate(BaseModel):
    """Payload for updating an existing workspace."""

    workspace_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="Updated name of the workspace",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Updated description",
    )
    status: str | None = Field(
        default=None,
        description="Updated status (active, suspended, archived)",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None:
            normalized = value.strip().lower()
            allowed = {"active", "suspended", "archived"}
            if normalized not in allowed:
                raise ValueError(f"status must be one of: {', '.join(allowed)}")
            return normalized
        return value


class WorkspaceResponse(WorkspaceBase):
    """Public representation of a workspace entity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique workspace UUID")
    tenant_id: uuid.UUID = Field(..., description="Parent tenant UUID")
    workspace_slug: str = Field(..., description="Unique URL slug")
    status: str = Field(..., description="Current lifecycle state")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class WorkspaceListResponse(BaseModel):
    """Paginated collection of workspaces."""

    items: list[WorkspaceResponse]
    total: int = Field(..., ge=0, description="Total count of matching workspaces")
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1)
