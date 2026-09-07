"""DatasetMetadata database model for Phase 2.3 Dataset Metadata Management."""

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin

class DatasetMetadata(Base, TimestampMixin):
    """Dataset metadata ORM model for storing extracted structure and statistics."""

    __tablename__ = "dataset_metadata"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id", ondelete="CASCADE"), primary_key=True
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Stores a list of strings
    column_names: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    
    # Stores a dict mapping column name to its basic type
    column_types: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Stores detailed column stats: array of dicts
    columns_metadata: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    
    # Stores dict mapping classification (e.g. "numeric") to list of column names
    classifications: Mapped[dict] = mapped_column(JSON, nullable=False)

    def __repr__(self) -> str:
        return f"<DatasetMetadata dataset_id={self.dataset_id!r} rows={self.row_count} cols={self.column_count}>"
