"""Project ORM model organizing initiatives and datasets within a workspace."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.workspace import Workspace

logger = logging.getLogger(__name__)


class Project(Base, TimestampMixin):
    """Project database entity scoping analytical workloads within a workspace."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "project_name", name="uq_projects_workspace_name"),
        Index("ix_projects_workspace_status", "workspace_id", "status"),
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="projects", foreign_keys=[workspace_id])

    def __repr__(self) -> str:
        return f"<Project id={self.id!r} name={self.project_name!r} status={self.status!r} workspace_id={self.workspace_id!r}>"

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": str(self.id),
            "workspace_id": str(self.workspace_id),
            "project_name": self.project_name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
