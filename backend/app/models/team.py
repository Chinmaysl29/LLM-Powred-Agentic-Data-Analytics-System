"""Team ORM model grouping collaborating individuals within a department."""

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

logger = logging.getLogger(__name__)


class Team(Base, TimestampMixin):
    """Team database entity representing an operational team within a department."""

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    team_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="",
    )

    __table_args__ = (
        UniqueConstraint("department_id", "team_name", name="uq_teams_department_name"),
        Index("ix_teams_department", "department_id"),
    )

    # Relationships
    department = relationship("Department", back_populates="teams", foreign_keys=[department_id])

    def __repr__(self) -> str:
        return f"<Team id={self.id!r} name={self.team_name!r} department_id={self.department_id!r}>"

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": str(self.id),
            "department_id": str(self.department_id),
            "team_name": self.team_name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
