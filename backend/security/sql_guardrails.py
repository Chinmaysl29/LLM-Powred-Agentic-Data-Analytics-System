"""SQL guardrails for the security layer — delegates to sandbox and SQLGuardrailsService."""

from backend.app.services.sql_guardrails_service import SQLGuardrailsService, get_sql_guardrails_service
from backend.security.sandbox import (
    SQLSandboxViolation,
    sanitize_sql as legacy_sanitize_sql,
    validate_sql_safety as legacy_validate_sql_safety,
)
from backend.sql_agent.sql_guardrails import SQLGuardrails

_guardrails_service = SQLGuardrailsService()


def validate_sql_safety(sql: str, allowed_tables: list[str] | None = None) -> bool:
    """Validate query safety using enhanced SQL Guardrails service."""
    # Run legacy check first
    legacy_validate_sql_safety(sql)

    # Run comprehensive guardrails check
    res = _guardrails_service.evaluate_query(sql=sql, allowed_tables=allowed_tables)
    if not res.is_safe:
        pattern = res.violations[0] if res.violations else "UNSAFE_QUERY"
        raise SQLSandboxViolation(
            f"Query contains forbidden or unsafe operation: {'; '.join(res.violations)}",
            pattern=pattern,
        )
    return True


def sanitize_sql(sql: str, max_limit: int | None = None) -> str:
    """Sanitize SQL query and apply row limit."""
    return _guardrails_service.sanitize_sql(sql=sql, max_limit=max_limit)


__all__ = [
    "SQLSandboxViolation",
    "sanitize_sql",
    "validate_sql_safety",
    "SQLGuardrails",
    "SQLGuardrailsService",
]
