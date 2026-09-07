"""Department ORM model grouping functional units within a workspace."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.team import Team
    from backend.app.models.workspace import Workspace

logger = logging.getLogger(__name__)


class Department(Base, TimestampMixin):
    """Department entity grouping functional teams within a workspace."""

    __tablename__ = "departments"

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

    department_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="",
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "department_name", name="uq_departments_workspace_name"),
        Index("ix_departments_workspace", "workspace_id"),
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="departments", foreign_keys=[workspace_id])
    teams = relationship("Team", back_populates="department", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Department id={self.id!r} name={self.department_name!r} workspace_id={self.workspace_id!r}>"

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": str(self.id),
            "workspace_id": str(self.workspace_id),
            "department_name": self.department_name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
