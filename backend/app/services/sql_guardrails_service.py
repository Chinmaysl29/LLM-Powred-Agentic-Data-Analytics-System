"""SQL Guardrails Service for enterprise query security.

Inspects incoming SQL queries to enforce read-only operations, block destructive commands,
detect SQL injection vectors, validate table/column identifiers against schema metadata,
enforce query limits, and assign quantitative risk tiers.
"""

import logging
import re
from typing import Any

import sqlparse
from sqlparse.sql import Identifier, IdentifierList, Where
from sqlparse.tokens import Keyword, Whitespace

from backend.app.schemas.sql_guardrails import (
    RiskLevel,
    SQLGuardrailResult,
    SQLViolation,
)

logger = logging.getLogger(__name__)

# Destructive & administrative operations that are never permitted
FORBIDDEN_KEYWORDS: list[re.Pattern[str]] = [
    re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA|INDEX|VIEW|PROCEDURE|FUNCTION|TRIGGER)\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE(\s+TABLE)?\b", re.IGNORECASE),
    re.compile(r"\bALTER\s+(TABLE|DATABASE|SCHEMA|INDEX|VIEW)\b", re.IGNORECASE),
    re.compile(r"\bCREATE\s+(TABLE|DATABASE|SCHEMA|INDEX|VIEW|PROCEDURE|FUNCTION|TRIGGER)\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+(FROM\b)?", re.IGNORECASE),
    re.compile(r"\bUPDATE\s+[a-zA-Z0-9_.]+\s+SET\b", re.IGNORECASE),
    re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    re.compile(r"\b(GRANT|REVOKE)\b", re.IGNORECASE),
    re.compile(r"\b(EXEC|EXECUTE|CALL)\b", re.IGNORECASE),
    re.compile(r"\b(MERGE\s+INTO|REPLACE\s+INTO)\b", re.IGNORECASE),
    re.compile(r"\b(VACUUM|REINDEX)\b", re.IGNORECASE),
    re.compile(r"\bxp_\w+", re.IGNORECASE),
]

# SQL injection patterns
INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r";\s*--", re.IGNORECASE), "SQL injection comment trick (; --)"),
    (re.compile(r"--[^\r\n]*", re.IGNORECASE), "SQL line comment (--), potential evasion"),
    (re.compile(r"/\*.*?\*/", re.DOTALL), "SQL block comment (/* */), potential evasion"),
    (re.compile(r"\bOR\s+('?1'?\s*=\s*'?1'?|true|'a'\s*=\s*'a')\b", re.IGNORECASE), "Tautology injection (OR 1=1)"),
    (re.compile(r"\bOR\s+(\d+)\s*=\s*\1\b", re.IGNORECASE), "Tautology injection (OR n=n)"),
    (re.compile(r"\b(PG_SLEEP|SLEEP|WAITFOR\s+DELAY|BENCHMARK)\b", re.IGNORECASE), "Time-delay blind injection function"),
    (re.compile(r"\b(pg_shadow|pg_authid|pg_user|sqlite_master|sqlite_schema|information_schema\.user_privileges)\b", re.IGNORECASE), "Privileged system catalog access attempt"),
]

# SQL Keywords to filter out during identifier extraction
SQL_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "JOIN", "INNER", "LEFT", "RIGHT", "FULL", "OUTER",
    "CROSS", "ON", "AS", "AND", "OR", "NOT", "IN", "IS", "NULL", "GROUP", "BY",
    "ORDER", "ASC", "DESC", "LIMIT", "OFFSET", "HAVING", "CASE", "WHEN", "THEN",
    "ELSE", "END", "DISTINCT", "ALL", "WITH", "UNION", "COUNT", "SUM", "AVG",
    "MIN", "MAX", "CAST", "BETWEEN", "LIKE", "ILIKE", "EXISTS", "COALESCE",
}


class SQLGuardrailsService:
    """Enterprise security gatekeeper evaluating SQL queries for safety, injection, and compliance."""

    def __init__(
        self,
        default_max_limit: int = 1000,
        enforce_read_only: bool = True,
    ) -> None:
        self._default_max_limit = default_max_limit
        self._enforce_read_only = enforce_read_only

    def evaluate_query(
        self,
        sql: str,
        allowed_tables: list[str] | None = None,
        schema_context: dict[str, Any] | None = None,
        max_limit: int | None = None,
        enforce_limit: bool = True,
    ) -> SQLGuardrailResult:
        """Comprehensively evaluate a SQL query against security guardrails."""
        target_limit = max_limit or self._default_max_limit
        raw_sql = sql.strip()

        logger.info("Evaluating SQL query safety (length=%d, max_limit=%d)", len(raw_sql), target_limit)

        violations: list[SQLViolation] = []
        risk_score = 0

        # Check 1: Empty Query
        if not raw_sql:
            violations.append(
                SQLViolation(
                    violation_type="SYNTAX_ERROR",
                    message="Query is empty or contains only whitespace",
                    severity="HIGH",
                )
            )
            return SQLGuardrailResult(
                is_safe=False,
                violations=["Query is empty or contains only whitespace"],
                risk_level="HIGH",
                risk_score=75,
                structured_violations=violations,
                sanitized_sql=None,
            )

        # Check 2: Destructive / Modification Keywords (Regex & AST)
        for pat in FORBIDDEN_KEYWORDS:
            match = pat.search(raw_sql)
            if match:
                matched_kw = match.group(0).strip()
                violations.append(
                    SQLViolation(
                        violation_type="DESTRUCTIVE_OPERATION",
                        message=f"Dangerous operation detected: '{matched_kw}' is forbidden",
                        severity="CRITICAL",
                        details={"matched": matched_kw},
                    )
                )
                risk_score += 85

        # Check 3: Statement Count & Stacked Queries (Injection Protection)
        parsed_statements = [s for s in sqlparse.parse(raw_sql) if str(s).strip() and str(s).strip() != ";"]

        if len(parsed_statements) > 1:
            violations.append(
                SQLViolation(
                    violation_type="SQL_INJECTION",
                    message="Stacked queries detected; multiple SQL statements separated by semicolons are strictly prohibited",
                    severity="CRITICAL",
                    details={"statement_count": len(parsed_statements)},
                )
            )
            risk_score += 90

        # Check 4: Root Command Read-Only Enforcement
        if parsed_statements:
            first_stmt = parsed_statements[0]
            stmt_type = first_stmt.get_type().upper()
            if stmt_type not in ("SELECT", "UNKNOWN"):
                violations.append(
                    SQLViolation(
                        violation_type="NON_READ_ONLY",
                        message=f"Only read-only SELECT or WITH queries are permitted; received statement of type '{stmt_type}'",
                        severity="CRITICAL",
                    )
                )
                risk_score += 80
            else:
                # Confirm text starts with SELECT or WITH
                clean_start = re.sub(r"/\*.*?\*/", "", raw_sql, flags=re.DOTALL).strip()
                if not re.match(r"^(SELECT|WITH)\b", clean_start, re.IGNORECASE):
                    violations.append(
                        SQLViolation(
                            violation_type="NON_READ_ONLY",
                            message="Query must begin with a read-only keyword (SELECT or WITH)",
                            severity="CRITICAL",
                        )
                    )
                    risk_score += 80

        # Check 5: SQL Injection Heuristics
        for inj_pat, desc in INJECTION_PATTERNS:
            if inj_pat.search(raw_sql):
                is_catalog = "catalog" in desc
                severity: RiskLevel = "CRITICAL" if is_catalog or "Tautology" in desc or "trick" in desc else "HIGH"
                violations.append(
                    SQLViolation(
                        violation_type="SQL_INJECTION" if not is_catalog else "SYSTEM_CATALOG_ACCESS",
                        message=f"SQL injection risk detected: {desc}",
                        severity=severity,
                        details={"pattern_description": desc},
                    )
                )
                risk_score += (75 if severity == "CRITICAL" else 40)

        # Check 6: Extract & Validate Tables
        detected_tables = self._extract_tables(raw_sql)
        valid_table_set: set[str] | None = None

        if allowed_tables:
            valid_table_set = {t.lower().strip() for t in allowed_tables}
        elif schema_context:
            tables_in_ctx = schema_context.get("tables", [])
            valid_table_set = set()
            for t in tables_in_ctx:
                if isinstance(t, dict):
                    valid_table_set.add(t.get("table_name", "").lower())
                    valid_table_set.add(t.get("table", "").lower())
                elif hasattr(t, "table_name"):
                    valid_table_set.add(t.table_name.lower())
                elif isinstance(t, str):
                    valid_table_set.add(t.lower())

        if valid_table_set is not None and detected_tables:
            for tbl in detected_tables:
                if tbl.lower() not in valid_table_set:
                    violations.append(
                        SQLViolation(
                            violation_type="UNAUTHORIZED_TABLE",
                            message=f"Unauthorized or unknown table reference: '{tbl}'",
                            severity="HIGH",
                            details={"table": tbl},
                        )
                    )
                    risk_score += 45

        # Check 7: Extract & Validate Columns
        detected_columns = self._extract_columns(raw_sql)
        if schema_context and detected_tables:
            table_column_map = self._build_table_column_map(schema_context)
            if table_column_map and len(detected_tables) == 1:
                single_tbl = detected_tables[0].lower()
                known_cols = table_column_map.get(single_tbl, set())
                if known_cols:
                    for col in detected_columns:
                        if col.lower() not in known_cols and not col.startswith("*") and not col.isdigit():
                            violations.append(
                                SQLViolation(
                                    violation_type="UNKNOWN_COLUMN",
                                    message=f"Column '{col}' does not exist in table '{single_tbl}'",
                                    severity="MEDIUM",
                                    details={"table": single_tbl, "column": col},
                                )
                            )
                            risk_score += 25

        # Check 8: Query Limit Enforcement
        sanitized_sql, applied_limit, limit_violation = self._enforce_query_limit(
            sql=raw_sql,
            max_limit=target_limit,
            enforce_limit=enforce_limit,
        )
        if limit_violation:
            violations.append(limit_violation)
            risk_score += (15 if limit_violation.severity == "LOW" else 25)

        # Risk Tier Calculation
        risk_score = max(0, min(100, risk_score))
        if any(v.severity == "CRITICAL" for v in violations) or risk_score >= 80:
            risk_level: RiskLevel = "CRITICAL"
        elif any(v.severity == "HIGH" for v in violations) or risk_score >= 50:
            risk_level = "HIGH"
        elif any(v.severity == "MEDIUM" for v in violations) or risk_score >= 20:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Safe if no critical/high violations and risk <= 50
        is_safe = (
            risk_level in ("LOW", "MEDIUM")
            and not any(v.severity in ("CRITICAL", "HIGH") for v in violations)
        )

        violation_messages = [v.message for v in violations]

        logger.info(
            "Query evaluation complete: is_safe=%s risk_level=%s score=%d violations=%d",
            is_safe,
            risk_level,
            risk_score,
            len(violations),
        )

        return SQLGuardrailResult(
            is_safe=is_safe,
            violations=violation_messages,
            risk_level=risk_level,
            risk_score=risk_score,
            structured_violations=violations,
            tables_detected=detected_tables,
            columns_detected=detected_columns,
            sanitized_sql=sanitized_sql if is_safe else None,
            applied_limit=applied_limit,
        )

    def sanitize_sql(self, sql: str, max_limit: int | None = None) -> str:
        """Sanitize SQL by normalizing formatting, trimming semicolons, and enforcing row limit."""
        target_limit = max_limit or self._default_max_limit
        sanitized, _, _ = self._enforce_query_limit(sql=sql, max_limit=target_limit, enforce_limit=True)
        return sanitized

    def _extract_tables(self, sql: str) -> list[str]:
        """Extract table names referenced in FROM, JOIN, and INTO clauses."""
        tables: list[str] = []
        # Match FROM and JOIN clauses
        patterns = [
            r"\bFROM\s+([a-zA-Z0-9_.]+)",
            r"\bJOIN\s+([a-zA-Z0-9_.]+)",
        ]
        for pat in patterns:
            for match in re.finditer(pat, sql, re.IGNORECASE):
                raw_tbl = match.group(1).strip().strip("`'\"")
                # Strip schema if public.sales
                tbl_name = raw_tbl.split(".")[-1]
                if tbl_name.upper() not in SQL_KEYWORDS and tbl_name not in tables:
                    tables.append(tbl_name)
        return tables

    def _extract_columns(self, sql: str) -> list[str]:
        """Extract column names referenced in SELECT projection and WHERE filter clauses."""
        columns: list[str] = []
        # Match simple SELECT ... FROM
        select_match = re.search(r"\bSELECT\s+(.*?)\s+\bFROM\b", sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            raw_cols = select_match.group(1).split(",")
            for col_expr in raw_cols:
                col_expr = col_expr.strip()
                # If aliased (col AS alias)
                if re.search(r"\bAS\b", col_expr, re.IGNORECASE):
                    col_expr = re.split(r"\bAS\b", col_expr, flags=re.IGNORECASE)[0].strip()
                # If function call like SUM(revenue) -> extract revenue
                func_match = re.search(r"\b\w+\s*\(\s*([a-zA-Z0-9_.*]+)\s*\)", col_expr)
                if func_match:
                    col_name = func_match.group(1).strip()
                else:
                    col_name = col_expr.strip().split(".")[-1].strip("`'\"")

                if col_name and col_name.upper() not in SQL_KEYWORDS and col_name not in columns:
                    columns.append(col_name)
        return columns

    def _build_table_column_map(self, schema_context: dict[str, Any]) -> dict[str, set[str]]:
        """Map table names to their known column sets from schema context."""
        mapping: dict[str, set[str]] = {}
        tables = schema_context.get("tables", [])
        for t in tables:
            t_name = ""
            cols: set[str] = set()
            if isinstance(t, dict):
                t_name = (t.get("table_name") or t.get("table") or "").lower()
                raw_cols = t.get("columns") or t.get("column_names") or []
                for c in raw_cols:
                    if isinstance(c, dict):
                        cols.add(c.get("name", "").lower())
                    elif isinstance(c, str):
                        cols.add(c.lower())
            elif hasattr(t, "table_name"):
                t_name = t.table_name.lower()
                cols = {c.name.lower() for c in getattr(t, "columns", [])}

            if t_name:
                mapping[t_name] = cols
        return mapping

    def _enforce_query_limit(
        self,
        sql: str,
        max_limit: int,
        enforce_limit: bool,
    ) -> tuple[str, int, SQLViolation | None]:
        """Detect and clamp or inject LIMIT into the query."""
        clean_sql = sql.strip().rstrip(";")
        clean_sql = re.sub(r"\s+", " ", clean_sql)

        limit_match = re.search(r"\bLIMIT\s+(\d+)\b", clean_sql, re.IGNORECASE)
        violation: SQLViolation | None = None
        applied_limit = max_limit

        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit > max_limit:
                violation = SQLViolation(
                    violation_type="LIMIT_EXCEEDED",
                    message=f"Specified LIMIT ({existing_limit}) exceeds maximum permitted threshold ({max_limit})",
                    severity="MEDIUM",
                    details={"existing_limit": existing_limit, "max_limit": max_limit},
                )
                if enforce_limit:
                    clean_sql = re.sub(r"\bLIMIT\s+\d+\b", f"LIMIT {max_limit}", clean_sql, flags=re.IGNORECASE)
                    applied_limit = max_limit
                else:
                    applied_limit = existing_limit
            else:
                applied_limit = existing_limit
        else:
            violation = SQLViolation(
                violation_type="MISSING_LIMIT",
                message="Query does not specify a LIMIT clause; an automated safeguard limit will be applied",
                severity="LOW",
                details={"enforced_limit": max_limit},
            )
            if enforce_limit:
                clean_sql = f"{clean_sql} LIMIT {max_limit}"
                applied_limit = max_limit

        return clean_sql, applied_limit, violation


def get_sql_guardrails_service() -> SQLGuardrailsService:
    """FastAPI dependency injection provider for SQLGuardrailsService."""
    return SQLGuardrailsService()
