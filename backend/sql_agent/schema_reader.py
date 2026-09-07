"""SQL Agent Schema Reader module.

Provides the SchemaReader interface for the SQL Intelligence Layer,
enabling schema discovery, relationship resolution, and prompt context generation.
"""

import logging
from typing import Any
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.app.repositories.schema_repository import SchemaRepository
from backend.app.schemas.schema_reader import (
    ColumnMetadata,
    DatabaseMetadata,
    DatabaseSchema,
    ForeignKeyMetadata,
    IndexMetadata,
    RelationshipMetadata,
    TableMetadata,
)
from backend.app.services.schema_reader_service import SchemaReaderService

logger = logging.getLogger(__name__)


class SchemaReader:
    """Core schema introspection component for the SQL Agent pipeline."""

    def __init__(
        self,
        bind: Engine | Session | None = None,
        cache_ttl_seconds: int = 300,
        service: SchemaReaderService | None = None,
    ) -> None:
        if service is not None:
            self._service = service
        elif bind is not None:
            repo = SchemaRepository(bind=bind)
            self._service = SchemaReaderService(schema_repository=repo, cache_ttl_seconds=cache_ttl_seconds)
        else:
            self._service = SchemaReaderService(cache_ttl_seconds=cache_ttl_seconds)

    @property
    def service(self) -> SchemaReaderService:
        """Access the underlying SchemaReaderService."""
        return self._service

    def get_schema(
        self,
        force_refresh: bool = False,
        schema_name: str | None = None,
        table_names: list[str] | None = None,
    ) -> DatabaseSchema:
        """Read and cache database schema structure."""
        return self._service.get_schema(
            force_refresh=force_refresh,
            schema_name=schema_name,
            table_names=table_names,
        )

    def get_table(self, table_name: str, schema_name: str | None = None) -> TableMetadata | None:
        """Get detailed metadata for a single table."""
        return self._service.get_table_schema(table_name=table_name, schema_name=schema_name)

    def get_compact_tables(self, schema_name: str | None = None) -> list[dict[str, Any]]:
        """Get compact table representations: [{'table': 'sales', 'columns': [...]}]"""
        return self._service.get_compact_tables(schema_name=schema_name)

    def to_prompt_context(self, table_names: list[str] | None = None, schema_name: str | None = None) -> str:
        """Generate formatted DDL/markdown schema for LLM SQL generation prompts."""
        return self._service.generate_prompt_context(table_names=table_names, schema_name=schema_name)

    def invalidate_cache(self) -> None:
        """Clear cached schema definitions."""
        self._service.invalidate_cache()


__all__ = [
    "SchemaReader",
    "DatabaseSchema",
    "TableMetadata",
    "ColumnMetadata",
    "IndexMetadata",
    "ForeignKeyMetadata",
    "RelationshipMetadata",
    "DatabaseMetadata",
]
