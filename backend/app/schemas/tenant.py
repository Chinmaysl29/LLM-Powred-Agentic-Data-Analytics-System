"""Tenant Pydantic schemas for request validation and API serialization."""

from __future__ import annotations

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TenantBase(BaseModel):
    """Base fields shared across tenant representations."""

    tenant_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Official human-readable name of the organization",
        examples=["Acme Corporation"],
    )


class TenantCreate(TenantBase):
    """Payload for registering a new tenant organization."""

    tenant_slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Optional custom URL-friendly identifier",
        examples=["acme-corp"],
    )
    tenant_status: str = Field(
        default="active",
        description="Initial lifecycle status",
        examples=["active"],
    )

    @field_validator("tenant_slug")
    @classmethod
    def validate_slug_format(cls, value: str | None) -> str | None:
        if value is not None:
            normalized = value.strip().lower()
            import re
            if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", normalized):
                raise ValueError(
                    "tenant_slug must consist of lowercase alphanumeric characters separated by single hyphens"
                )
            return normalized
        return value


class TenantUpdate(BaseModel):
    """Payload for updating an existing tenant organization."""

    tenant_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="Updated name of the organization",
    )
    tenant_status: str | None = Field(
        default=None,
        description="Updated lifecycle status (active, suspended, archived)",
    )

    @field_validator("tenant_status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None:
            normalized = value.strip().lower()
            allowed = {"active", "suspended", "archived", "provisioning"}
            if normalized not in allowed:
                raise ValueError(f"tenant_status must be one of: {', '.join(allowed)}")
            return normalized
        return value


class TenantResponse(TenantBase):
    """Public representation of an enterprise tenant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique tenant UUID identifier")
    tenant_slug: str = Field(..., description="Unique tenant slug")
    tenant_status: str = Field(..., description="Current lifecycle status")
    created_at: datetime = Field(..., description="Timestamp when tenant was created")
    updated_at: datetime = Field(..., description="Timestamp of latest tenant update")


class TenantListResponse(BaseModel):
    """Paginated collection response of tenants."""

    items: list[TenantResponse]
    total: int = Field(..., ge=0, description="Total number of tenants matching query")
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1)
