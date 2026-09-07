"""Workspace ORM model for departmental and project-level enterprise isolation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.department import Department
    from backend.app.models.project import Project
    from backend.app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class Workspace(Base, TimestampMixin):
    """Workspace database entity scoping projects, departments, and assets within a tenant."""

    __tablename__ = "workspaces"

    # Primary key UUID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique workspace identifier",
    )

    # Parent tenant foreign key
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key reference to parent tenant organization",
    )

    # Human-readable workspace name
    workspace_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Display name of the workspace (e.g., 'Finance Analytics')",
    )

    # URL-friendly slug unique within the tenant
    workspace_slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="URL-friendly identifier unique within the tenant organization",
    )

    # Optional description of workspace purpose
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="",
        doc="Detailed description or charter of the workspace",
    )

    # Lifecycle status: active, suspended, archived
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        index=True,
        doc="Lifecycle state of the workspace",
    )

    # Unique constraint per tenant and composite performance indexes
    __table_args__ = (
        UniqueConstraint("tenant_id", "workspace_slug", name="uq_workspaces_tenant_slug"),
        Index("ix_workspaces_tenant_status", "tenant_id", "status"),
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id], lazy="selectin")
    departments = relationship("Department", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")
    projects = relationship("Project", back_populates="workspace", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Workspace id={self.id!r} tenant_id={self.tenant_id!r} name={self.workspace_name!r} slug={self.workspace_slug!r} status={self.status!r}>"

    def to_dict(self) -> dict[str, str | None]:
        """Serialize workspace entity to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "workspace_name": self.workspace_name,
            "workspace_slug": self.workspace_slug,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
