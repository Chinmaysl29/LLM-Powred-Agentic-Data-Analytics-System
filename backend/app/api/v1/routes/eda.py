"""API routes for EDA (Exploratory Data Analysis) Agent."""

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Query

from backend.app.schemas.eda import EDAResponse, EDAResults
from backend.app.services.eda_service import EDAService, get_eda_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eda", tags=["EDA"])


@router.get(
    "/{dataset_id}",
    response_model=EDAResponse,
    summary="Execute Exploratory Data Analysis on a dataset",
)
async def run_eda_analysis(
    dataset_id: str,
    version: int | None = Query(None, description="Dataset version to analyze"),
    sample_size: int | None = Query(None, description="Max rows to sample"),
    eda_service: EDAService = Depends(get_eda_service),
) -> EDAResponse:
    """Run automated EDA on the specified dataset and return structured analysis."""
    start_time = time.perf_counter()
    logger.info("Received EDA request for dataset_id=%s version=%s", dataset_id, version)

    eda_results = await eda_service.analyze_dataset(
        dataset_id=dataset_id,
        version_number=version,
        sample_size=sample_size,
    )

    duration_ms = (time.perf_counter() - start_time) * 1000
    return EDAResponse(
        dataset_id=dataset_id,
        status="success",
        execution_time_ms=round(duration_ms, 2),
        eda_results=eda_results,
    )
