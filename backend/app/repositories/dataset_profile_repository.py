"""Dataset profile repository providing CRUD operations."""

import logging
from typing import Any

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db_session
from backend.app.models.dataset_profile import DatasetProfile

logger = logging.getLogger(__name__)


class DatasetProfileRepository:
    """Repository handling persistence and retrieval of DatasetProfile entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @property
    def session(self) -> Session:
        """Backward-compatible alias for the database session."""
        return self.db

    def create(self, profile: DatasetProfile) -> DatasetProfile:
        """Persist a new DatasetProfile record."""
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        logger.info(
            "Created dataset profile record dataset_id=%s duplicates=%d",
            profile.dataset_id,
            profile.duplicate_rows,
        )
        return profile

    def get(self, dataset_id: str) -> DatasetProfile | None:
        """Retrieve DatasetProfile by dataset_id."""
        stmt = select(DatasetProfile).where(DatasetProfile.dataset_id == dataset_id)
        profile = self.db.scalars(stmt).first()
        if profile:
            logger.debug("Retrieved dataset profile record dataset_id=%s", dataset_id)
        else:
            logger.warning("Dataset profile record not found dataset_id=%s", dataset_id)
        return profile

    def delete(self, dataset_id: str) -> bool:
        """Delete DatasetProfile by dataset_id."""
        profile = self.get(dataset_id)
        if not profile:
            return False

        self.db.delete(profile)
        self.db.commit()
        logger.info("Deleted dataset profile record dataset_id=%s", dataset_id)
        return True


def get_dataset_profile_repository(db: Session = Depends(get_db_session)) -> DatasetProfileRepository:
    """FastAPI dependency yielding a DatasetProfileRepository instance."""
    return DatasetProfileRepository(db=db)
