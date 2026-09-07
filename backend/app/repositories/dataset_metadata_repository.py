"""Dataset metadata repository providing CRUD database operations."""

import logging
from typing import Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db_session
from backend.app.models.dataset_metadata import DatasetMetadata

logger = logging.getLogger(__name__)


class DatasetMetadataRepository:
    """Repository handling persistence and retrieval of DatasetMetadata entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @property
    def session(self) -> Session:
        """Backward-compatible alias for the database session."""
        return self.db

    def create(self, metadata: DatasetMetadata) -> DatasetMetadata:
        """Persist a new DatasetMetadata record to the database."""
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(metadata)
        logger.info(
            "Created dataset metadata record dataset_id=%s rows=%d cols=%d",
            metadata.dataset_id,
            metadata.row_count,
            metadata.column_count,
        )
        return metadata

    def get(self, dataset_id: str) -> DatasetMetadata | None:
        """Retrieve DatasetMetadata by dataset_id."""
        stmt = select(DatasetMetadata).where(DatasetMetadata.dataset_id == dataset_id)
        metadata = self.db.scalars(stmt).first()
        if metadata:
            logger.debug("Retrieved dataset metadata record dataset_id=%s", dataset_id)
        else:
            logger.warning("Dataset metadata record not found dataset_id=%s", dataset_id)
        return metadata

    def update(self, dataset_id: str, **kwargs: Any) -> DatasetMetadata | None:
        """Update fields of an existing DatasetMetadata record."""
        metadata = self.get(dataset_id)
        if not metadata:
            logger.warning("Cannot update non-existent dataset metadata dataset_id=%s", dataset_id)
            return None

        for key, value in kwargs.items():
            if hasattr(metadata, key) and value is not None:
                setattr(metadata, key, value)

        self.db.commit()
        self.db.refresh(metadata)
        logger.info("Updated dataset metadata record dataset_id=%s updated_fields=%s", dataset_id, list(kwargs.keys()))
        return metadata
        
    def delete(self, dataset_id: str) -> bool:
        """Delete DatasetMetadata by dataset_id."""
        metadata = self.get(dataset_id)
        if not metadata:
            logger.warning("Cannot delete non-existent dataset metadata dataset_id=%s", dataset_id)
            return False

        self.db.delete(metadata)
        self.db.commit()
        logger.info("Deleted dataset metadata record dataset_id=%s", dataset_id)
        return True


def get_dataset_metadata_repository(db: Session = Depends(get_db_session)) -> DatasetMetadataRepository:
    """FastAPI dependency yielding a DatasetMetadataRepository instance."""
    return DatasetMetadataRepository(db=db)
