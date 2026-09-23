"""Pydantic schemas for Phase 4.2 SQL Guardrails.

Defines models for query safety evaluation, risk tier classification,
violation logging, table/column verification, and sanitized SQL generation.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

ViolationType = Literal[
    "DESTRUCTIVE_OPERATION",
    "NON_READ_ONLY",
    "SQL_INJECTION",
    "UNAUTHORIZED_TABLE",
    "UNKNOWN_COLUMN",
    "MISSING_LIMIT",
    "LIMIT_EXCEEDED",
    "SYSTEM_CATALOG_ACCESS",
    "SYNTAX_ERROR",
]


class SQLViolation(BaseModel):
    """Detailed record of a single guardrail violation."""

    model_config = ConfigDict(from_attributes=True)

    violation_type: str = Field(..., description="Classification of the violation")
    message: str = Field(..., description="Human-readable explanation of why the query was flagged")
    severity: RiskLevel = Field(..., description="Severity classification: LOW, MEDIUM, HIGH, CRITICAL")
    details: dict[str, Any] | None = Field(default=None, description="Additional context or matched token")


class SQLGuardrailResult(BaseModel):
    """Standard output schema for SQL Guardrails verification."""

    model_config = ConfigDict(from_attributes=True)

    is_safe: bool = Field(..., description="Whether the query passed all security checks without blocking issues")
    violations: list[str] = Field(
        default_factory=list, description="List of violation messages (empty if query is completely safe)"
    )
    risk_level: RiskLevel = Field(..., description="Overall risk classification: LOW, MEDIUM, HIGH, CRITICAL")
    risk_score: int = Field(default=0, ge=0, le=100, description="Quantitative risk score (0=safe, 100=critical)")
    structured_violations: list[SQLViolation] = Field(
        default_factory=list, description="Structured violation records with metadata"
    )
    tables_detected: list[str] = Field(default_factory=list, description="Table names parsed from the query")
    columns_detected: list[str] = Field(default_factory=list, description="Column names parsed from the query")
    sanitized_sql: str | None = Field(
        default=None, description="Sanitized and limit-enforced query ready for safe execution"
    )
    applied_limit: int | None = Field(default=None, description="Row limit applied or verified")


class SQLGuardrailRequest(BaseModel):
    """API request payload for evaluating a SQL query."""

    sql: str = Field(..., min_length=1, max_length=10000, description="SQL query to validate")
    allowed_tables: list[str] | None = Field(
        default=None, description="Optional explicit allowlist of table names"
    )
    schema_context: dict[str, Any] | None = Field(
        default=None, description="Optional schema context dictionary containing tables and columns"
    )
    max_limit: int = Field(default=1000, ge=1, le=100000, description="Maximum permitted row limit")
    enforce_limit: bool = Field(
        default=True, description="Whether to automatically inject or clamp LIMIT in sanitized_sql"
    )


class SQLGuardrailResponse(BaseModel):
    """API response envelope for SQL Guardrails evaluation."""

    model_config = ConfigDict(from_attributes=True)

    status: str = Field(default="success", description="Response status")
    guardrail_result: SQLGuardrailResult = Field(..., description="Detailed evaluation outcome")
    evaluated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of the guardrail check",
    )
