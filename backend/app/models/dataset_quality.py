"""DatasetQuality database model for Phase 2.5 Data Quality Engine."""

from sqlalchemy import Float, String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class DatasetQuality(Base, TimestampMixin):
    """Dataset quality ORM model for storing quality scores."""

    __tablename__ = "dataset_quality"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id", ondelete="CASCADE"), primary_key=True
    )
    completeness_score: Mapped[float] = mapped_column(Float, nullable=False)
    uniqueness_score: Mapped[float] = mapped_column(Float, nullable=False)
    consistency_score: Mapped[float] = mapped_column(Float, nullable=False)
    validity_score: Mapped[float] = mapped_column(Float, nullable=False)
    integrity_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_classification: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        Index("ix_dataset_quality_dataset_id_created_at", "dataset_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<DatasetQuality dataset_id={self.dataset_id!r} score={self.overall_score} class={self.quality_classification}>"
