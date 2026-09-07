"""DatasetProfile database model for Phase 2.4 Data Profiling Engine."""

from sqlalchemy import Float, Integer, String, ForeignKey
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class DatasetProfile(Base, TimestampMixin):
    """Dataset profile ORM model for storing statistical analysis results."""

    __tablename__ = "dataset_profiles"

    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id", ondelete="CASCADE"), primary_key=True
    )
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Stores MissingDataProfile as JSON: { null_count, null_percentage, columns_with_missing }
    missing_data_profile: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Stores CardinalityProfile as JSON: { high_cardinality_columns, low_cardinality_columns }
    cardinality_profile: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Stores dict mapping column name to NumericProfile
    numeric_columns_profile: Mapped[dict] = mapped_column(JSON, nullable=False)

    def __repr__(self) -> str:
        return f"<DatasetProfile dataset_id={self.dataset_id!r} duplicates={self.duplicate_rows}>"
