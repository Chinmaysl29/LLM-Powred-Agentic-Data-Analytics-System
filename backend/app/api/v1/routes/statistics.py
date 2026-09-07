"""API routes for Statistics Agent."""

import logging
import time

from fastapi import APIRouter, Depends, Query

from backend.app.schemas.statistics import StatisticsResponse
from backend.app.services.statistics_service import (
    StatisticsService,
    get_statistics_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get(
    "/{dataset_id}",
    response_model=StatisticsResponse,
    summary="Execute Statistical Analysis and Hypothesis Testing",
)
async def run_statistics_analysis(
    dataset_id: str,
    version: int | None = Query(None, description="Dataset version to analyze"),
    target_column: str | None = Query(None, description="Optional target column for regression analysis"),
    sample_size: int | None = Query(None, description="Max rows to sample"),
    statistics_service: StatisticsService = Depends(get_statistics_service),
) -> StatisticsResponse:
    """Run inferential statistical analysis on the specified dataset and return structured results."""
    start_time = time.perf_counter()
    logger.info("Received Statistics request for dataset_id=%s version=%s", dataset_id, version)

    stat_results = await statistics_service.analyze_dataset(
        dataset_id=dataset_id,
        version_number=version,
        target_column=target_column,
        sample_size=sample_size,
    )

    duration_ms = (time.perf_counter() - start_time) * 1000
    return StatisticsResponse(
        dataset_id=dataset_id,
        status="success",
        execution_time_ms=round(duration_ms, 2),
        statistics_results=stat_results,
    )
