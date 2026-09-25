"""Comprehensive tests for Phase 4.2 SQL Guardrails.

Verifies:
1. Permitting safe read-only SQL queries (SELECT, WITH, JOIN, GROUP BY, ORDER BY, LIMIT).
2. Blocking destructive DDL/DML queries (DROP, DELETE, TRUNCATE, ALTER, UPDATE, INSERT, GRANT).
3. Detecting stacked query injections (semicolon separation).
4. Detecting SQL injection patterns (tautology, comment evasion, time delays, system catalog).
5. Table validation against explicit allowlists and schema context.
6. Column validation against schema definitions.
7. Query limit enforcement (auto-injection of missing limits, clamping of excessive limits).
8. Risk scoring and risk tier assignments (LOW, MEDIUM, HIGH, CRITICAL).
9. SQLGuardrails facade in backend.sql_agent.sql_guardrails.
10. Backward compatibility with backend.security.sql_guardrails.
11. REST API endpoints (/api/v1/sql/guardrails/check and /sanitize).
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.schemas.sql_guardrails import SQLGuardrailResult
from backend.app.services.sql_guardrails_service import SQLGuardrailsService
from backend.main import app
from backend.security.sandbox import SQLSandboxViolation
from backend.security.sql_guardrails import (
    sanitize_sql,
    validate_sql_safety,
)
from backend.sql_agent.sql_guardrails import SQLGuardrails


@pytest.fixture
def guardrails_service() -> SQLGuardrailsService:
    return SQLGuardrailsService(default_max_limit=1000)


@pytest.fixture
def mock_schema_context() -> dict:
    return {
        "tables": [
            {
                "table_name": "sales",
                "column_names": ["order_id", "customer_id", "revenue", "region", "order_date"],
            },
            {
                "table_name": "customers",
                "column_names": ["customer_id", "customer_name", "email", "country"],
            },
        ]
    }


# ----------------------------------------------------------------------
# 1. Safe Read-Only Queries
# ----------------------------------------------------------------------
def test_safe_queries_pass(guardrails_service: SQLGuardrailsService):
    safe_queries = [
        "SELECT order_id, revenue FROM sales WHERE revenue > 100 LIMIT 50",
        "SELECT region, SUM(revenue) AS total FROM sales GROUP BY region HAVING SUM(revenue) > 1000 ORDER BY total DESC LIMIT 10",
        "SELECT s.order_id, c.customer_name FROM sales s JOIN customers c ON s.customer_id = c.customer_id LIMIT 100",
        "WITH regional_avg AS (SELECT region, AVG(revenue) as avg_rev FROM sales GROUP BY region) SELECT * FROM regional_avg LIMIT 10",
    ]

    for q in safe_queries:
        result = guardrails_service.evaluate_query(q)
        assert result.is_safe is True
        assert result.risk_level in ("LOW", "MEDIUM")
        assert len(result.violations) == 0 or all("LIMIT" in v for v in result.violations)


# ----------------------------------------------------------------------
# 2. Destructive Queries Blocked
# ----------------------------------------------------------------------
def test_destructive_queries_blocked(guardrails_service: SQLGuardrailsService):
    destructive_queries = [
        "DROP TABLE datasets",
        "DROP DATABASE production",
        "DELETE FROM sales WHERE order_id = 5",
        "TRUNCATE TABLE audit_logs",
        "ALTER TABLE customers ADD COLUMN is_admin BOOLEAN",
        "UPDATE sales SET revenue = 0 WHERE region = 'North'",
        "INSERT INTO sales (order_id, revenue) VALUES (999, 500)",
        "GRANT ALL PRIVILEGES ON DATABASE test TO attacker",
        "CREATE TABLE backdoor (id INT)",
        "EXEC xp_cmdshell('whoami')",
    ]

    for q in destructive_queries:
        result = guardrails_service.evaluate_query(q)
        assert result.is_safe is False
        assert result.risk_level == "CRITICAL"
        assert any("Dangerous operation detected" in v or "forbidden" in v for v in result.violations)


# ----------------------------------------------------------------------
# 3. Stacked Query Injection Blocked
# ----------------------------------------------------------------------
def test_stacked_query_injection_blocked(guardrails_service: SQLGuardrailsService):
    stacked = "SELECT * FROM sales; DROP TABLE customers;"
    result = guardrails_service.evaluate_query(stacked)

    assert result.is_safe is False
    assert result.risk_level == "CRITICAL"
    assert any("Stacked queries detected" in v for v in result.violations)


# ----------------------------------------------------------------------
# 4. SQL Injection Patterns Blocked
# ----------------------------------------------------------------------
def test_sql_injection_patterns(guardrails_service: SQLGuardrailsService):
    # Tautology injection
    tautology_q = "SELECT * FROM sales WHERE order_id = 1 OR 1=1 LIMIT 10"
    res_tautology = guardrails_service.evaluate_query(tautology_q)
    assert res_tautology.is_safe is False
    assert any("Tautology injection" in v for v in res_tautology.violations)

    # Comment evasion injection
    comment_q = "SELECT * FROM sales WHERE order_id = 1; -- comment"
    res_comment = guardrails_service.evaluate_query(comment_q)
    assert res_comment.is_safe is False

    # Privileged system catalog access
    catalog_q = "SELECT * FROM pg_shadow LIMIT 10"
    res_catalog = guardrails_service.evaluate_query(catalog_q)
    assert res_catalog.is_safe is False
    assert any("system catalog" in v.lower() for v in res_catalog.violations)

    # Time-delay blind injection
    sleep_q = "SELECT * FROM sales WHERE order_id = 1 AND PG_SLEEP(5) LIMIT 1"
    res_sleep = guardrails_service.evaluate_query(sleep_q)
    assert res_sleep.is_safe is False
    assert any("Time-delay" in v for v in res_sleep.violations)


# ----------------------------------------------------------------------
# 5. Table Validation (Allowlist & Schema)
# ----------------------------------------------------------------------
def test_table_validation(guardrails_service: SQLGuardrailsService, mock_schema_context: dict):
    # Safe allowed table
    valid_q = "SELECT * FROM sales LIMIT 10"
    res_valid = guardrails_service.evaluate_query(valid_q, schema_context=mock_schema_context)
    assert res_valid.is_safe is True
    assert "sales" in res_valid.tables_detected

    # Disallowed / Unknown table
    unknown_q = "SELECT * FROM unauthorized_financial_records LIMIT 10"
    res_unknown = guardrails_service.evaluate_query(unknown_q, schema_context=mock_schema_context)
    assert res_unknown.is_safe is False
    assert any("Unauthorized or unknown table" in v for v in res_unknown.violations)

    # Test with explicit allowed_tables list
    res_explicit = guardrails_service.evaluate_query(
        "SELECT * FROM sales JOIN payroll ON sales.id = payroll.id LIMIT 10",
        allowed_tables=["sales"],
    )
    assert res_explicit.is_safe is False
    assert any("payroll" in v for v in res_explicit.violations)


# ----------------------------------------------------------------------
# 6. Column Validation
# ----------------------------------------------------------------------
def test_column_validation(guardrails_service: SQLGuardrailsService, mock_schema_context: dict):
    # Valid columns exist in schema
    valid_q = "SELECT order_id, revenue FROM sales LIMIT 10"
    res_valid = guardrails_service.evaluate_query(valid_q, schema_context=mock_schema_context)
    assert res_valid.is_safe is True

    # Unknown / fake column in sales
    fake_col_q = "SELECT fake_column FROM sales LIMIT 10"
    res_fake = guardrails_service.evaluate_query(fake_col_q, schema_context=mock_schema_context)
    assert any("Column 'fake_column' does not exist in table 'sales'" in v for v in res_fake.violations)


# ----------------------------------------------------------------------
# 7. Query Limit Enforcement
# ----------------------------------------------------------------------
def test_query_limit_enforcement(guardrails_service: SQLGuardrailsService):
    # Missing limit -> automatically injected in sanitized_sql
    unbounded_q = "SELECT * FROM sales"
    res_unbounded = guardrails_service.evaluate_query(unbounded_q, max_limit=500)
    assert any("does not specify a LIMIT" in v for v in res_unbounded.violations)
    assert res_unbounded.sanitized_sql is not None
    assert "LIMIT 500" in res_unbounded.sanitized_sql

    # Excessive limit -> clamped in sanitized_sql
    excessive_q = "SELECT * FROM sales LIMIT 50000"
    res_excessive = guardrails_service.evaluate_query(excessive_q, max_limit=1000)
    assert any("exceeds maximum permitted threshold" in v for v in res_excessive.violations)
    assert res_excessive.sanitized_sql is not None
    assert "LIMIT 1000" in res_excessive.sanitized_sql

    # Acceptable limit
    acceptable_q = "SELECT * FROM sales LIMIT 200"
    res_acceptable = guardrails_service.evaluate_query(acceptable_q, max_limit=1000)
    assert res_acceptable.applied_limit == 200
    assert "LIMIT 200" in res_acceptable.sanitized_sql


# ----------------------------------------------------------------------
# 8. SQL Agent SQLGuardrails Facade
# ----------------------------------------------------------------------
def test_sql_agent_guardrails_facade():
    guardrails = SQLGuardrails()

    # Valid query
    res = guardrails.evaluate_query("SELECT * FROM sales LIMIT 10")
    assert isinstance(res, SQLGuardrailResult)
    assert res.is_safe is True

    # Validate method returns True for safe
    assert guardrails.validate("SELECT * FROM sales LIMIT 10") is True

    # Validate method raises SQLSandboxViolation for destructive
    with pytest.raises(SQLSandboxViolation):
        guardrails.validate("DROP TABLE sales")

    # Sanitize method applies limit
    sanitized = guardrails.sanitize("SELECT * FROM sales", max_limit=100)
    assert "LIMIT 100" in sanitized


# ----------------------------------------------------------------------
# 9. Backward Compatibility with backend.security.sql_guardrails
# ----------------------------------------------------------------------
def test_security_sql_guardrails_backward_compatibility():
    # Safe query passes
    assert validate_sql_safety("SELECT * FROM sales LIMIT 10") is True

    # Destructive query raises SQLSandboxViolation
    with pytest.raises(SQLSandboxViolation):
        validate_sql_safety("DROP TABLE sales")

    with pytest.raises(SQLSandboxViolation):
        validate_sql_safety("DELETE FROM customers")

    # sanitize_sql trims and normalizes
    clean = sanitize_sql("SELECT  *   FROM  sales;   ", max_limit=50)
    assert "LIMIT 50" in clean
    assert ";" not in clean


# ----------------------------------------------------------------------
# 10. REST API Endpoints
# ----------------------------------------------------------------------
def test_api_guardrails_endpoints():
    client = TestClient(app)

    # 1. POST /api/v1/sql/guardrails/check (Safe query)
    resp_safe = client.post(
        "/api/v1/sql/guardrails/check",
        json={"sql": "SELECT order_id, revenue FROM sales LIMIT 10"},
    )
    assert resp_safe.status_code == 200
    data_safe = resp_safe.json()
    assert data_safe["status"] == "success"
    assert data_safe["guardrail_result"]["is_safe"] is True
    assert data_safe["guardrail_result"]["risk_level"] in ("LOW", "MEDIUM")

    # 2. POST /api/v1/sql/guardrails/check (Destructive query)
    resp_bad = client.post(
        "/api/v1/sql/guardrails/check",
        json={"sql": "DROP TABLE critical_data"},
    )
    assert resp_bad.status_code == 200
    data_bad = resp_bad.json()
    assert data_bad["guardrail_result"]["is_safe"] is False
    assert data_bad["guardrail_result"]["risk_level"] == "CRITICAL"
    assert len(data_bad["guardrail_result"]["violations"]) > 0

    # 3. POST /api/v1/sql/guardrails/sanitize
    resp_san = client.post(
        "/api/v1/sql/guardrails/sanitize",
        json={"sql": "SELECT * FROM sales", "max_limit": 250},
    )
    assert resp_san.status_code == 200
    data_san = resp_san.json()
    assert "LIMIT 250" in data_san["sanitized_sql"]
