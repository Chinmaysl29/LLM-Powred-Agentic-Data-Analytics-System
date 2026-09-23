"""Pydantic schemas for Phase 3.7 Validation Agent."""

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


ValidationStatus = Literal["PASSED", "WARNING", "FAILED"]
AuditCheckStatus = Literal["passed", "warning", "failed"]


class AuditLogEntry(BaseModel):
    """Record of an individual validation check performed for auditability."""

    check_name: str = Field(..., description="Name of the validation check")
    agent_target: str = Field(..., description="Agent or module evaluated")
    status: AuditCheckStatus = Field(..., description="Outcome: passed, warning, or failed")
    message: str = Field(..., description="Details or failure reason")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO timestamp of the validation check",
    )


class ValidationResult(BaseModel):
    """Standardized result schema for the Validation Agent."""

    model_config = ConfigDict(from_attributes=True)

    validation_status: ValidationStatus = Field(..., description="Overall status: PASSED, WARNING, or FAILED")
    confidence_score: int = Field(..., ge=0, le=100, description="Confidence score from 0 to 100")
    warnings: list[str] = Field(default_factory=list, description="Non-blocking warning messages")
    errors: list[str] = Field(default_factory=list, description="Critical validation error messages")
    audit_log: list[AuditLogEntry] = Field(
        default_factory=list, description="Comprehensive audit trail of all checks executed"
    )


class ValidationRequest(BaseModel):
    """Request payload for direct API validation."""

    results: dict[str, Any] = Field(default_factory=dict, description="Agent execution results map to validate")
    query: str | None = Field(None, description="Original user query")
    dataset_id: str | None = Field(None, description="Dataset ID")
    sql_query: str | None = Field(None, description="Optional SQL query to safety-check")
    chart_config: dict[str, Any] | None = Field(None, description="Optional visualization chart configuration")


class SQLValidationRequest(BaseModel):
    """Request schema for validating SQL query safety."""

    sql: str = Field(..., description="SQL query string to validate")
    allowed_tables: list[str] | None = Field(None, description="Optional list of allowed table names")


class SQLValidationResult(BaseModel):
    """Safety check result for a SQL query."""

    is_safe: bool = Field(..., description="Whether query passed safety rules")
    blocked_keywords: list[str] = Field(default_factory=list, description="List of unsafe keywords found")
    message: str = Field(..., description="Detailed safety assessment")


class ValidationResponse(BaseModel):
    """API response envelope for validation operations."""

    status: str = Field("success", description="API execution status")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    validation_result: ValidationResult = Field(..., description="Comprehensive validation results")
