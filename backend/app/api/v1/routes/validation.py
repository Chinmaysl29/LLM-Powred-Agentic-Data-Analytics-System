"""API routes for Validation Agent."""

import logging
import time
from fastapi import APIRouter, Depends

from backend.app.schemas.validation import (
    SQLValidationRequest,
    SQLValidationResult,
    ValidationRequest,
    ValidationResponse,
)
from backend.app.services.validation_service import (
    ValidationService,
    get_validation_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/validation", tags=["Validation"])


@router.post(
    "/validate",
    response_model=ValidationResponse,
    summary="Validate multi-agent workflow results",
)
async def validate_results(
    request: ValidationRequest,
    validation_service: ValidationService = Depends(get_validation_service),
) -> ValidationResponse:
    """Execute complete validation suite across provided analytical results."""
    start_time = time.perf_counter()
    logger.info("Received validation request with %d result keys", len(request.results))

    payload = dict(request.results)
    if request.sql_query:
        payload["sql_query"] = request.sql_query
    if request.chart_config:
        payload["visualization"] = {"primary_chart": request.chart_config}

    val_result = validation_service.validate_results(
        results=payload,
        query=request.query,
    )

    duration_ms = (time.perf_counter() - start_time) * 1000
    return ValidationResponse(
        status="success",
        execution_time_ms=round(duration_ms, 2),
        validation_result=val_result,
    )


@router.post(
    "/validate-sql",
    response_model=SQLValidationResult,
    summary="Safety-check a SQL query",
)
async def validate_sql(
    request: SQLValidationRequest,
    validation_service: ValidationService = Depends(get_validation_service),
) -> SQLValidationResult:
    """Validate that a SQL query contains no destructive or unsafe statements."""
    return validation_service.validate_sql(
        sql_query=request.sql,
        allowed_tables=request.allowed_tables,
    )
