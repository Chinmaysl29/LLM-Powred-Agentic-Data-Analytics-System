"""Analysis ORM model for storing analysis results and AI-generated insights."""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin


class Analysis(Base, TimestampMixin):
    """Persisted result of an AI-driven analysis on a dataset."""

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Foreign key reference
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id"), nullable=False, index=True
    )
    analysis_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # eda, forecast, sql_query, recommendation, report, etc.
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Analysis {self.analysis_type} status={self.status}>"
