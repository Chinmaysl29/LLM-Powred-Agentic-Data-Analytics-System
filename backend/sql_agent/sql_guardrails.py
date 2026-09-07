"""SQL Agent SQL Guardrails module.

Provides the SQLGuardrails security barrier for the SQL Intelligence Layer,
blocking destructive queries, verifying table/column validity, detecting injection,
and enforcing enterprise row limits.
"""

import logging
from typing import Any

from backend.app.schemas.sql_guardrails import (
    RiskLevel,
    SQLGuardrailResult,
    SQLViolation,
)
from backend.app.services.sql_guardrails_service import (
    SQLGuardrailsService,
    get_sql_guardrails_service,
)
from backend.security.sandbox import SQLSandboxViolation

logger = logging.getLogger(__name__)


class SQLGuardrails:
    """Security guardrail engine for validating and sanitizing queries in the SQL pipeline."""

    def __init__(self, service: SQLGuardrailsService | None = None) -> None:
        self._service = service or get_sql_guardrails_service()

    @property
    def service(self) -> SQLGuardrailsService:
        """Access underlying service."""
        return self._service

    def evaluate_query(
        self,
        sql: str,
        allowed_tables: list[str] | None = None,
        schema_context: dict[str, Any] | None = None,
        max_limit: int | None = None,
        enforce_limit: bool = True,
    ) -> SQLGuardrailResult:
        """Evaluate query safety against all security rules."""
        return self._service.evaluate_query(
            sql=sql,
            allowed_tables=allowed_tables,
            schema_context=schema_context,
            max_limit=max_limit,
            enforce_limit=enforce_limit,
        )

    def validate(
        self,
        sql: str,
        allowed_tables: list[str] | None = None,
        schema_context: dict[str, Any] | None = None,
    ) -> bool:
        """Validate query safety, raising SQLSandboxViolation if unsafe."""
        result = self.evaluate_query(sql=sql, allowed_tables=allowed_tables, schema_context=schema_context)
        if not result.is_safe:
            violation_summary = "; ".join(result.violations)
            logger.warning("SQL guardrail blocked query: %s (risk=%s)", violation_summary, result.risk_level)
            raise SQLSandboxViolation(
                message=f"Query rejected by SQL Guardrails: {violation_summary}",
                pattern=result.violations[0] if result.violations else "UNSAFE_SQL",
            )
        return True

    def sanitize(self, sql: str, max_limit: int | None = None) -> str:
        """Sanitize query formatting and enforce row limit."""
        return self._service.sanitize_sql(sql=sql, max_limit=max_limit)


__all__ = [
    "SQLGuardrails",
    "SQLGuardrailResult",
    "SQLViolation",
    "RiskLevel",
    "SQLSandboxViolation",
]
