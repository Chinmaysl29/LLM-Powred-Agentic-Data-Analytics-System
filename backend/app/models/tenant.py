"""Tenant ORM model for multi-tenant enterprise isolation.

Provides the foundational database entity for organizations, workspaces,
RBAC, data governance, and multi-company SaaS partitioning.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin

logger = logging.getLogger(__name__)


class Tenant(Base, TimestampMixin):
    """Tenant ORM model representing an enterprise organization."""

    __tablename__ = "tenants"

    # Primary key UUID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique identifier for the tenant organization",
    )

    # Human-readable organization name
    tenant_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Official display name of the tenant organization",
    )

    # Unique URL-friendly slug
    tenant_slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique slug used in subdomains, route resolution, and API scoping",
    )

    # Lifecycle status: active, suspended, archived, provisioning
    tenant_status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        index=True,
        doc="Lifecycle state: active, suspended, archived",
    )

    # Table constraints & composite indexes for query performance
    __table_args__ = (
        UniqueConstraint("tenant_slug", name="uq_tenants_tenant_slug"),
        Index("ix_tenants_status_created", "tenant_status", "created_at"),
    )

    # Future multi-tenant relationship declarations
    # Note: Using string references with primaryjoin/foreign_keys allows loose coupling
    # until foreign key columns are added to target tables in subsequent migrations.
    users = relationship(
        "User",
        primaryjoin="foreign(User.tenant_id) == Tenant.id" if hasattr(Base, "_tenant_col_ready") else None,
        lazy="selectin",
        viewonly=True,
        uselist=True,
    ) if hasattr(Base, "_tenant_col_ready") else None

    def __repr__(self) -> str:
        return f"<Tenant id={self.id!r} name={self.tenant_name!r} slug={self.tenant_slug!r} status={self.tenant_status!r}>"

    def to_dict(self) -> dict[str, str]:
        """Serialize tenant to standard dictionary format."""
        return {
            "id": str(self.id),
            "tenant_name": self.tenant_name,
            "tenant_slug": self.tenant_slug,
            "tenant_status": self.tenant_status,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }
