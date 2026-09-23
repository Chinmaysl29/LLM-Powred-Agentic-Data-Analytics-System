"""SQL execution sandbox to prevent dangerous operations."""

import logging
import re

logger = logging.getLogger(__name__)

# Patterns that are never allowed in user-submitted SQL
FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA|INDEX)\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bALTER\s+(TABLE|DATABASE)\b", re.IGNORECASE),
    re.compile(r"\bCREATE\s+(TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE),
    re.compile(r"\bGRANT\b", re.IGNORECASE),
    re.compile(r"\bREVOKE\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+\w+\s+SET\b", re.IGNORECASE),
    re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    re.compile(r";\s*--", re.IGNORECASE),  # SQL injection comment trick
    re.compile(r"\bEXEC(UTE)?\b", re.IGNORECASE),
    re.compile(r"\bxp_\w+", re.IGNORECASE),  # SQL Server extended procedures
]


class SQLSandboxViolation(Exception):
    """Raised when a SQL query violates sandbox rules."""

    def __init__(self, message: str, pattern: str) -> None:
        self.pattern = pattern
        super().__init__(message)


def validate_sql_safety(sql: str) -> bool:
    """Check a SQL query against the forbidden pattern list.

    Returns True if safe, raises SQLSandboxViolation if dangerous.
    """
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(sql):
            logger.warning("SQL sandbox violation: %s matched in query", pattern.pattern)
            raise SQLSandboxViolation(
                f"Query contains forbidden operation: {pattern.pattern}",
                pattern=pattern.pattern,
            )
    return True


def sanitize_sql(sql: str) -> str:
    """Remove trailing semicolons and normalize whitespace."""
    sql = sql.strip().rstrip(";")
    sql = re.sub(r"\s+", " ", sql)
    return sql
