"""Service layer for Phase 6.1 Forecasting Foundation.

Provides dependency-injected orchestration connecting datasets from DataRetrievalService
to the core ForecastingFoundation time-series validation and preparation engine.
"""

import logging
import time
from typing import Any

import pandas as pd
from fastapi import Depends

from backend.app.core.exceptions import DataRetrievalError
from backend.app.schemas.forecasting import (
    ForecastingFoundationConfig,
    ForecastingFoundationResponse,
    ValidationReport,
)
from backend.app.services.data_retrieval_service import (
    DataRetrievalService,
    get_data_retrieval_service,
)
from backend.forecasting.foundation import ForecastingFoundation, TimeSeriesValidator

logger = logging.getLogger(__name__)


class ForecastingFoundationService:
    """Enterprise service managing forecasting dataset validation and preparation."""

    def __init__(self, retrieval_service: DataRetrievalService | None = None) -> None:
        self._retrieval_service = retrieval_service

    def prepare_dataframe(
        self,
        df: pd.DataFrame,
        config: ForecastingFoundationConfig | None = None,
    ) -> ForecastingFoundationResponse:
        """Execute foundation pipeline directly on an in-memory DataFrame."""
        start_time = time.perf_counter()
        logger.info("Executing forecasting foundation on DataFrame shape=%s", df.shape)

        _, response = ForecastingFoundation.process_dataframe(df, config=config)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.execution_time_ms = round(duration_ms, 2)
        return response

    def get_prepared_dataframe(
        self,
        df: pd.DataFrame,
        config: ForecastingFoundationConfig | None = None,
    ) -> tuple[pd.DataFrame, ForecastingFoundationResponse]:
        """Execute foundation pipeline and return both prepared DataFrame and metadata response."""
        return ForecastingFoundation.process_dataframe(df, config=config)

    async def prepare_dataset(
        self,
        dataset_id: str,
        version_number: int | None = None,
        config: ForecastingFoundationConfig | None = None,
        sample_size: int | None = None,
    ) -> ForecastingFoundationResponse:
        """Retrieve dataset from storage/database and execute forecasting foundation."""
        if not self._retrieval_service:
            raise DataRetrievalError("DataRetrievalService not injected into ForecastingFoundationService")

        logger.info("Retrieving dataset %s (version=%s) for forecasting foundation", dataset_id, version_number)
        df, _ = self._retrieval_service.load_dataframe(
            dataset_id=dataset_id,
            version_number=version_number,
            sample_size=sample_size,
        )

        return self.prepare_dataframe(df, config=config)

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        time_col: str | None = None,
        target_col: str | None = None,
        frequency: str = "monthly",
    ) -> ValidationReport:
        """Execute validation checks only without full feature engineering."""
        return TimeSeriesValidator.validate(
            df=df,
            time_col=time_col,
            target_col=target_col,
            frequency=frequency,
        )


def get_forecasting_foundation_service(
    retrieval_service: DataRetrievalService = Depends(get_data_retrieval_service),
) -> ForecastingFoundationService:
    """FastAPI dependency provider for ForecastingFoundationService."""
    return ForecastingFoundationService(retrieval_service=retrieval_service)
