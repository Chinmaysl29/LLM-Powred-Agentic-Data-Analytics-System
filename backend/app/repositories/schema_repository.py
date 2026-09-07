"""Schema Repository for database introspection using SQLAlchemy.

Extracts dynamic relational schema details across PostgreSQL and SQLite,
including tables, views, columns, datatypes, primary keys, foreign keys, and indexes.
"""

import logging
from typing import Any
from sqlalchemy import Engine, inspect
from sqlalchemy.orm import Session

from backend.app.schemas.schema_reader import (
    ColumnMetadata,
    DatabaseMetadata,
    DatabaseSchema,
    ForeignKeyMetadata,
    IndexMetadata,
    RelationshipMetadata,
    TableMetadata,
)

logger = logging.getLogger(__name__)


class SchemaRepository:
    """Repository handling database metadata introspection via SQLAlchemy inspector."""

    def __init__(self, bind: Engine | Session) -> None:
        if isinstance(bind, Session):
            self._engine = bind.get_bind()
        else:
            self._engine = bind

    @property
    def engine(self) -> Engine:
        """Access underlying SQLAlchemy Engine."""
        return self._engine

    def inspect_schema(
        self,
        schema_name: str | None = None,
        table_names: list[str] | None = None,
        include_views: bool = False,
    ) -> DatabaseSchema:
        """Inspect and return complete structured database schema."""
        logger.info("Introspecting database schema (schema=%s, dialect=%s)", schema_name, self._engine.dialect.name)
        inspector = inspect(self._engine)

        available_tables = inspector.get_table_names(schema=schema_name)
        if include_views:
            try:
                available_tables.extend(inspector.get_view_names(schema=schema_name))
            except Exception as exc:
                logger.debug("Could not inspect view names: %s", exc)

        # Filter tables if explicit list provided
        if table_names:
            target_set = {t.lower().strip() for t in table_names}
            tables_to_inspect = [t for t in available_tables if t.lower() in target_set]
        else:
            tables_to_inspect = available_tables

        tables: list[TableMetadata] = []
        relationships: list[RelationshipMetadata] = []

        for table_name in tables_to_inspect:
            table_meta = self._inspect_table(inspector, table_name, schema_name)
            tables.append(table_meta)

            # Accumulate relationships from foreign keys
            for fk in table_meta.foreign_keys:
                relationships.append(
                    RelationshipMetadata(
                        source_table=table_name,
                        source_columns=fk.source_columns,
                        target_table=fk.target_table,
                        target_columns=fk.target_columns,
                        constraint_name=fk.constraint_name,
                    )
                )

        database_name = getattr(self._engine.url, "database", None)
        meta = DatabaseMetadata(
            dialect=self._engine.dialect.name,
            database_name=database_name,
            schema_name=schema_name or ("public" if self._engine.dialect.name == "postgresql" else "main"),
            table_count=len(tables),
            relationship_count=len(relationships),
            is_cached=False,
        )

        logger.info(
            "Schema introspection complete: %d tables, %d relationships discovered",
            len(tables),
            len(relationships),
        )

        return DatabaseSchema(
            tables=tables,
            relationships=relationships,
            metadata=meta,
        )

    def _inspect_table(
        self,
        inspector: Any,
        table_name: str,
        schema_name: str | None,
    ) -> TableMetadata:
        """Extract column, primary key, foreign key, and index metadata for one table."""
        # Primary keys
        pk_constraint = inspector.get_pk_constraint(table_name, schema=schema_name) or {}
        primary_keys: list[str] = pk_constraint.get("constrained_columns") or []
        pk_set = set(primary_keys)

        # Columns
        raw_columns = inspector.get_columns(table_name, schema=schema_name)
        columns: list[ColumnMetadata] = []
        column_names: list[str] = []

        for c in raw_columns:
            c_name = c["name"]
            column_names.append(c_name)
            is_pk = bool(c.get("primary_key", False)) or (c_name in pk_set)
            columns.append(
                ColumnMetadata(
                    name=c_name,
                    data_type=str(c["type"]),
                    nullable=bool(c.get("nullable", True)),
                    default=str(c.get("default")) if c.get("default") is not None else None,
                    primary_key=is_pk,
                    autoincrement=bool(c.get("autoincrement", False)),
                    comment=c.get("comment"),
                )
            )

        # Foreign keys
        raw_fks = inspector.get_foreign_keys(table_name, schema=schema_name)
        foreign_keys: list[ForeignKeyMetadata] = []
        for fk in raw_fks:
            foreign_keys.append(
                ForeignKeyMetadata(
                    source_table=table_name,
                    source_columns=fk.get("constrained_columns") or [],
                    target_table=fk.get("referred_table", ""),
                    target_columns=fk.get("referred_columns") or [],
                    constraint_name=fk.get("name"),
                )
            )

        # Indexes
        raw_indexes = inspector.get_indexes(table_name, schema=schema_name)
        indexes: list[IndexMetadata] = []
        for idx in raw_indexes:
            indexes.append(
                IndexMetadata(
                    name=idx.get("name"),
                    columns=idx.get("column_names") or [],
                    unique=bool(idx.get("unique", False)),
                )
            )

        # Table comment
        table_comment = None
        try:
            comment_dict = inspector.get_table_comment(table_name, schema=schema_name)
            table_comment = comment_dict.get("text") if isinstance(comment_dict, dict) else None
        except Exception:
            pass

        return TableMetadata(
            table_name=table_name,
            schema_name=schema_name,
            columns=columns,
            column_names=column_names,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            comment=table_comment,
        )
