"""Repository providing database operations for the ForecastRun model."""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.forecast_run import ForecastRun

logger = logging.getLogger(__name__)


class ForecastRunRepository:
    """Repository handling persistence and retrieval of ForecastRun records."""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def save_run(
        self,
        run_id: str,
        model_type: str,
        target: str,
        params: dict[str, Any],
        output: dict[str, Any],
    ) -> ForecastRun | None:
        """Persist a forecast run outcome to the database."""
        if self.db is None:
            logger.debug("Database session not provided; skipping ForecastRun persistence for run_id=%s", run_id)
            return None

        forecast_run = ForecastRun(
            run_id=run_id,
            model_type=model_type,
            target=target,
            params=params,
            output=output,
        )
        try:
            self.db.add(forecast_run)
            self.db.commit()
            self.db.refresh(forecast_run)
            logger.info("Persisted ForecastRun run_id=%s model_type=%s target=%s", run_id, model_type, target)
            return forecast_run
        except Exception as e:
            self.db.rollback()
            logger.warning("Failed to persist ForecastRun run_id=%s: %s", run_id, e)
            return None

    def get_run(self, run_id: str) -> ForecastRun | None:
        """Retrieve a single ForecastRun record by run_id."""
        if self.db is None:
            return None
        stmt = select(ForecastRun).where(ForecastRun.run_id == run_id)
        return self.db.scalars(stmt).first()

    def list_runs(self, model_type: str | None = None, limit: int = 50) -> list[ForecastRun]:
        """List past forecast runs, optionally filtered by model_type."""
        if self.db is None:
            return []
        stmt = select(ForecastRun)
        if model_type:
            stmt = stmt.where(ForecastRun.model_type == model_type)
        stmt = stmt.order_by(ForecastRun.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())
