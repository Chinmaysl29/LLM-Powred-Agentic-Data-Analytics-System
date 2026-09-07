"""DatasetVersion database model for Phase 2.6 Dataset Versioning System."""

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.models.base import Base


class DatasetVersion(Base):
    """Dataset version ORM model for tracking lineage and snapshots."""

    __tablename__ = "dataset_versions"

    version_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("dataset_versions.version_id", ondelete="RESTRICT"), nullable=True
    )
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    transformation_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    metadata_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    quality_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # No duplicate version numbers per dataset
        Index("uq_dataset_version_number", "dataset_id", "version_number", unique=True),
        # Version >= 1
        CheckConstraint("version_number >= 1", name="chk_version_number_positive"),
        # Enforce only one active version per dataset (using a unique index where is_active is True)
        Index(
            "uq_dataset_active_version",
            "dataset_id",
            unique=True,
            postgresql_where=(is_active == True),
            sqlite_where=(is_active == True),
        ),
        # Fast history listing
        Index("ix_dataset_versions_history", "dataset_id", "created_at"),
        # Fast lineage traversal
        Index("ix_dataset_versions_parent", "parent_version_id"),
    )

    def __repr__(self) -> str:
        return f"<DatasetVersion {self.dataset_id} v{self.version_number} active={self.is_active}>"
