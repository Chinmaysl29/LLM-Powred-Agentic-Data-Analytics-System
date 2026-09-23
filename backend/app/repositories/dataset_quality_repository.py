"""Dataset quality repository providing CRUD operations."""

import logging
from typing import Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.database.postgres import get_db_session
from backend.app.models.dataset_quality import DatasetQuality

logger = logging.getLogger(__name__)


class DatasetQualityRepository:
    """Repository handling persistence and retrieval of DatasetQuality entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @property
    def session(self) -> Session:
        """Backward-compatible alias for the database session."""
        return self.db

    def create(self, quality: DatasetQuality) -> DatasetQuality:
        """Persist a new DatasetQuality record."""
        try:
            self.db.add(quality)
            self.db.commit()
            self.db.refresh(quality)
            logger.info(
                "Created quality record for dataset %s",
                quality.dataset_id,
            )
            return quality
        except IntegrityError as exc:
            self.db.rollback()
            logger.error("Failed to create quality record for dataset_id=%s: Duplicate or constraint error", quality.dataset_id)
            raise exc

    def get(self, dataset_id: str) -> DatasetQuality | None:
        """Retrieve latest DatasetQuality by dataset_id."""
        stmt = (
            select(DatasetQuality)
            .where(DatasetQuality.dataset_id == dataset_id)
            .order_by(DatasetQuality.created_at.desc())
            .limit(1)
        )
        quality = self.db.scalars(stmt).first()
        if quality:
            logger.debug("Retrieved quality record for dataset_id=%s", dataset_id)
        else:
            logger.warning("Quality record not found for dataset_id=%s", dataset_id)
        return quality


def get_dataset_quality_repository(db: Session = Depends(get_db_session)) -> DatasetQualityRepository:
    """FastAPI dependency yielding a DatasetQualityRepository instance."""
    return DatasetQualityRepository(db=db)
