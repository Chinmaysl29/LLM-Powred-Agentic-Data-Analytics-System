"""Forecast run database model for persistence of forecasting pipeline results."""

import uuid
from typing import Any

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class ForecastRun(Base, TimestampMixin):
    """ForecastRun ORM model representing executed and validated forecast operations."""

    __tablename__ = "forecast_runs"

    run_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target: Mapped[str] = mapped_column(String(100), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    output: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<ForecastRun run_id={self.run_id!r} model_type={self.model_type!r} target={self.target!r}>"
