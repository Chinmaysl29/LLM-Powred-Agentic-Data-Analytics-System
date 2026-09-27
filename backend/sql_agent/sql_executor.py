"""Enterprise SQL Execution Engine.

Executes queries safely against either PostgreSQL or in-memory SQLite tables
populated from dataset DataFrames. Strictly gates every execution behind SQLGuardrails.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.sql_agent.sql_guardrails import SQLGuardrails, SQLSandboxViolation

logger = logging.getLogger(__name__)


class SQLExecutionResult:
    """Standardized result format for executed SQL queries."""

    def __init__(
        self,
        columns: list[str],
        rows: list[dict[str, Any]],
        row_count: int,
        execution_time_ms: float,
        executed_sql: str,
        is_truncated: bool = False,
    ) -> None:
        self.columns = columns
        self.rows = rows
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.executed_sql = executed_sql
        self.is_truncated = is_truncated

    def to_dict(self) -> dict[str, Any]:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "executed_sql": self.executed_sql,
            "is_truncated": self.is_truncated,
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


class SQLExecutor:
    """Safe execution bridge with guardrail enforcement and multi-backend support."""

    def __init__(self, guardrails: SQLGuardrails | None = None) -> None:
        self._guardrails = guardrails or SQLGuardrails()

    def execute_on_dataframe(
        self,
        sql: str,
        df: pd.DataFrame,
        table_name: str = "dataset",
        max_rows: int = 1000,
    ) -> SQLExecutionResult:
        """Safely execute query against an in-memory SQLite table loaded from a pandas DataFrame."""
        # 1. Guardrail safety check
        self._guardrails.validate(sql=sql, allowed_tables=[table_name, f'"{table_name}"', "active_dataset"])
        sanitized_sql = self._guardrails.sanitize(sql=sql, max_limit=max_rows)

        start_time = time.perf_counter()

        # 2. In-memory SQLite isolated execution
        # Use isolated in-memory connection
        conn = sqlite3.connect(":memory:")
        try:
            # Normalize column names in df for sqlite compatibility
            clean_df = df.copy()
            clean_df.columns = [str(c).strip() for c in clean_df.columns]
            clean_df.to_sql(table_name, conn, index=False, if_exists="replace")

            # Also alias as active_dataset for generic queries
            if table_name != "active_dataset":
                clean_df.to_sql("active_dataset", conn, index=False, if_exists="replace")

            cursor = conn.cursor()
            cursor.execute(sanitized_sql)
            col_names = [desc[0] for desc in cursor.description] if cursor.description else []
            raw_rows = cursor.fetchall()

            rows = [dict(zip(col_names, row)) for row in raw_rows]
            duration = (time.perf_counter() - start_time) * 1000.0

            return SQLExecutionResult(
                columns=col_names,
                rows=rows,
                row_count=len(rows),
                execution_time_ms=duration,
                executed_sql=sanitized_sql,
                is_truncated=len(rows) >= max_rows,
            )
        finally:
            conn.close()

    def execute_on_postgres(
        self,
        sql: str,
        db_session: Session,
        allowed_tables: list[str] | None = None,
        max_rows: int = 1000,
    ) -> SQLExecutionResult:
        """Safely execute query against PostgreSQL database with guardrail validation."""
        self._guardrails.validate(sql=sql, allowed_tables=allowed_tables)
        sanitized_sql = self._guardrails.sanitize(sql=sql, max_limit=max_rows)

        start_time = time.perf_counter()
        result = db_session.execute(text(sanitized_sql))
        columns = list(result.keys()) if result.returns_rows else []
        raw_rows = result.fetchall() if result.returns_rows else []
        rows = [dict(zip(columns, row)) for row in raw_rows]
        duration = (time.perf_counter() - start_time) * 1000.0

        return SQLExecutionResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            execution_time_ms=duration,
            executed_sql=sanitized_sql,
            is_truncated=len(rows) >= max_rows,
        )


__all__ = ["SQLExecutor", "SQLExecutionResult", "SQLSandboxViolation"]
