"""API routes for SQL Schema Reader."""

import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.schemas.schema_reader import (
    DatabaseSchema,
    SchemaReaderResponse,
    TableMetadata,
)
from backend.app.services.schema_reader_service import (
    SchemaReaderService,
    get_schema_reader_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schema", tags=["SQL Schema Reader"])


@router.get(
    "",
    response_model=SchemaReaderResponse,
    summary="Inspect and retrieve database schema",
)
async def get_database_schema(
    refresh: bool = Query(False, description="Force refresh schema cache"),
    schema_name: str | None = Query(None, description="Database schema namespace (e.g. public)"),
    service: SchemaReaderService = Depends(get_schema_reader_service),
) -> SchemaReaderResponse:
    """Retrieve full database schema including tables, columns, foreign keys, and indexes."""
    try:
        schema_data = service.get_schema(force_refresh=refresh, schema_name=schema_name)
        return SchemaReaderResponse(
            status="success",
            schema_data=schema_data,
        )
    except Exception as exc:
        logger.error("Failed to read database schema: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema introspection error: {str(exc)}",
        )


@router.get(
    "/compact",
    response_model=list[dict[str, Any]],
    summary="Get compact prompt-ready table/column representations",
)
async def get_compact_schema(
    refresh: bool = Query(False, description="Force refresh schema cache"),
    schema_name: str | None = Query(None, description="Database schema namespace"),
    service: SchemaReaderService = Depends(get_schema_reader_service),
) -> list[dict[str, Any]]:
    """Retrieve lightweight table-column mappings: [{'table': 'sales', 'columns': [...]}]"""
    try:
        return service.get_compact_tables(schema_name=schema_name, force_refresh=refresh)
    except Exception as exc:
        logger.error("Failed to get compact schema: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema introspection error: {str(exc)}",
        )


@router.get(
    "/tables/{table_name}",
    response_model=TableMetadata,
    summary="Get detailed schema metadata for a single table",
)
async def get_table_schema(
    table_name: str,
    schema_name: str | None = Query(None, description="Database schema namespace"),
    refresh: bool = Query(False, description="Force refresh cache"),
    service: SchemaReaderService = Depends(get_schema_reader_service),
) -> TableMetadata:
    """Retrieve detailed column, index, and constraint information for a specific table."""
    table = service.get_table_schema(table_name=table_name, schema_name=schema_name, force_refresh=refresh)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table '{table_name}' was not found in schema",
        )
    return table


@router.get(
    "/prompt-context",
    response_model=dict[str, str],
    summary="Get formatted schema markdown for LLM SQL generation prompts",
)
async def get_prompt_context(
    tables: list[str] | None = Query(None, description="Optional subset of table names to include"),
    schema_name: str | None = Query(None, description="Database schema namespace"),
    service: SchemaReaderService = Depends(get_schema_reader_service),
) -> dict[str, str]:
    """Render formatted markdown DDL context for LLM prompt construction."""
    context_text = service.generate_prompt_context(table_names=tables, schema_name=schema_name)
    return {"prompt_context": context_text}


@router.post(
    "/refresh",
    response_model=dict[str, str],
    summary="Invalidate and refresh database schema cache",
)
async def refresh_schema_cache(
    service: SchemaReaderService = Depends(get_schema_reader_service),
) -> dict[str, str]:
    """Clear all in-memory cached schemas to force immediate re-introspection."""
    service.invalidate_cache()
    return {"status": "cache_invalidated", "message": "Schema cache successfully cleared"}
