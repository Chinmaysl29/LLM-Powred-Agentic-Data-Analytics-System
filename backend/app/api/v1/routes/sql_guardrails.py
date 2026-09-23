"""API routes for SQL Guardrails."""

import logging
from typing import Any
from fastapi import APIRouter, Depends

from backend.app.schemas.sql_guardrails import (
    SQLGuardrailRequest,
    SQLGuardrailResponse,
)
from backend.app.services.sql_guardrails_service import (
    SQLGuardrailsService,
    get_sql_guardrails_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sql/guardrails", tags=["SQL Guardrails"])


@router.post(
    "/check",
    response_model=SQLGuardrailResponse,
    summary="Evaluate SQL query safety and compliance against guardrails",
)
async def check_sql_safety(
    request: SQLGuardrailRequest,
    guardrails_service: SQLGuardrailsService = Depends(get_sql_guardrails_service),
) -> SQLGuardrailResponse:
    """Inspect query for destructive operations, SQL injection, schema validity, and limits."""
    result = guardrails_service.evaluate_query(
        sql=request.sql,
        allowed_tables=request.allowed_tables,
        schema_context=request.schema_context,
        max_limit=request.max_limit,
        enforce_limit=request.enforce_limit,
    )
    return SQLGuardrailResponse(
        status="success",
        guardrail_result=result,
    )


@router.post(
    "/sanitize",
    response_model=dict[str, Any],
    summary="Sanitize query and enforce safety row limit",
)
async def sanitize_sql_query(
    request: SQLGuardrailRequest,
    guardrails_service: SQLGuardrailsService = Depends(get_sql_guardrails_service),
) -> dict[str, Any]:
    """Return sanitized query with stripped semicolons, normalized whitespace, and enforced LIMIT."""
    sanitized = guardrails_service.sanitize_sql(
        sql=request.sql,
        max_limit=request.max_limit,
    )
    return {
        "status": "success",
        "original_sql": request.sql,
        "sanitized_sql": sanitized,
        "max_limit": request.max_limit,
    }
