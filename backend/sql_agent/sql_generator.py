"""Enterprise SQL Generator module.

Translates natural language questions into safe, optimized SQL queries using schema
awareness, column type resolution, and aggregations.
Supports both deterministic rule-based generation and LLM-assisted generation.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.app.llm.provider import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Enterprise text-to-SQL translation engine with schema grounding."""

    def __init__(
        self,
        llm: LLMProvider | None = None,
        schema_context: dict[str, Any] | None = None,
    ) -> None:
        self._llm = llm
        self.schema_context = schema_context or {}

    def generate_sql(
        self,
        query: str,
        table_name: str | None = None,
        columns: list[str] | None = None,
        column_types: dict[str, str] | None = None,
    ) -> str:
        """Alias for generate with schema_context auto-resolution."""
        tbl = table_name
        cols = columns
        dtypes = column_types
        if not tbl and self.schema_context.get("tables"):
            tbl = next(iter(self.schema_context["tables"].keys()))
            if not cols:
                cols = self.schema_context["tables"][tbl].get("columns", [])
        return self.generate(
            query=query,
            table_name=tbl or "dataset",
            columns=cols,
            column_types=dtypes,
        )

    def generate(
        self,
        query: str,
        table_name: str = "dataset",
        columns: list[str] | None = None,
        column_types: dict[str, str] | None = None,
    ) -> str:
        """Generate ANSI-SQL from natural language query given table and schema context."""
        cols = columns or []
        dtypes = column_types or {}

        # 1. If LLM is available and initialized, attempt prompt-driven generation
        if self._llm:
            try:
                sql = self._generate_with_llm(query, table_name, cols, dtypes)
                if sql and sql.strip().upper().startswith("SELECT"):
                    return self._clean_sql(sql)
            except Exception as e:
                logger.warning("LLM SQL generation fallback to deterministic engine: %s", e)

        # 2. Deterministic Rule-Based SQL Engine
        return self._generate_deterministic(query, table_name, cols, dtypes)

    def _generate_with_llm(
        self,
        query: str,
        table_name: str,
        columns: list[str],
        column_types: dict[str, str],
    ) -> str:
        schema_desc = ", ".join(f"{c} ({column_types.get(c, 'TEXT')})" for c in columns)
        prompt = (
            f"You are a Senior SQL Engineer. Generate ONLY a single safe ANSI-SQL SELECT query.\n"
            f"Table: {table_name}\n"
            f"Schema: {schema_desc}\n"
            f"Question: {query}\n"
            f"Rules:\n"
            f"- ONLY SELECT statements allowed\n"
            f"- Return RAW SQL query only, no markdown, no explanation\n"
            f"- Always quote columns if they have spaces or uppercase\n"
            f"- Apply proper LIMIT (max 1000)\n"
        )
        response = self._llm.generate(prompt)
        return self._clean_sql(response)

    def _generate_deterministic(
        self,
        query: str,
        table_name: str,
        columns: list[str],
        column_types: dict[str, str],
    ) -> str:
        """Generate robust SQL deterministically from natural language cues."""
        q_lower = query.lower()
        safe_table = f'"{table_name}"' if not table_name.isidentifier() else table_name

        if not columns:
            return f"SELECT * FROM {safe_table} LIMIT 100;"

        # Classify columns into numeric, temporal/date, and categorical
        numeric_cols: list[str] = []
        date_cols: list[str] = []
        categorical_cols: list[str] = []

        for col in columns:
            t = (column_types.get(col) or "").lower()
            c_lower = col.lower()
            if any(term in t for term in ("int", "float", "double", "decimal", "numeric", "real")) or any(
                term in c_lower for term in ("revenue", "sales", "amount", "profit", "price", "cost", "total", "qty", "quantity")
            ):
                numeric_cols.append(col)
            elif any(term in t for term in ("date", "time", "timestamp")) or any(
                term in c_lower for term in ("date", "month", "year", "quarter", "day", "time", "period")
            ):
                date_cols.append(col)
            else:
                categorical_cols.append(col)

        # Match metric column
        metric_col: str | None = None
        for col in numeric_cols:
            if re.search(rf"\b{re.escape(col.lower())}\b", q_lower):
                metric_col = col
                break
        if not metric_col and numeric_cols:
            metric_col = numeric_cols[0]

        # Match dimension / grouping column
        dimension_col: str | None = None
        for col in categorical_cols + date_cols:
            if re.search(rf"\b{re.escape(col.lower())}\b", q_lower):
                dimension_col = col
                break

        # Check for temporal intent like "by month", "monthly", "over time", "trend"
        if not dimension_col and any(term in q_lower for term in ("month", "monthly", "trend", "date", "over time", "yearly", "year")):
            if date_cols:
                dimension_col = date_cols[0]

        # Check for specific "top <N>" queries
        limit_match = re.search(r"\btop\s+(\d+)\b", q_lower)
        limit = int(limit_match.group(1)) if limit_match else 100

        def quote(c: str) -> str:
            return f'"{c}"' if not c.isidentifier() else c

        def alias(c: str) -> str:
            return c.replace('"', '').replace(' ', '_')

        # 1. Top N query (e.g., "Show top 10 customers")
        if "top" in q_lower or "best" in q_lower or "highest" in q_lower:
            dim = dimension_col or (categorical_cols[0] if categorical_cols else None)
            met = metric_col or (numeric_cols[0] if numeric_cols else "*")

            if dim and met != "*":
                met_alias = alias(met)
                return (
                    f"SELECT {quote(dim)}, SUM({quote(met)}) AS total_{met_alias} "
                    f"FROM {safe_table} "
                    f"GROUP BY {quote(dim)} "
                    f"ORDER BY total_{met_alias} DESC "
                    f"LIMIT {limit};"
                )
            elif met != "*":
                return f"SELECT * FROM {safe_table} ORDER BY {quote(met)} DESC LIMIT {limit};"

        # 2. Monthly / Temporal Revenue / Sales Trend (e.g., "Revenue by month", "monthly sales")
        if any(term in q_lower for term in ("month", "monthly", "trend", "revenue by", "sales by")):
            dim = dimension_col or (date_cols[0] if date_cols else (categorical_cols[0] if categorical_cols else None))
            met = metric_col or (numeric_cols[0] if numeric_cols else None)

            if dim and met:
                met_alias = alias(met)
                return (
                    f"SELECT {quote(dim)}, SUM({quote(met)}) AS total_{met_alias} "
                    f"FROM {safe_table} "
                    f"GROUP BY {quote(dim)} "
                    f"ORDER BY {quote(dim)} ASC "
                    f"LIMIT {limit};"
                )

        # 3. Average queries (e.g., "Average sales", "avg revenue")
        if any(term in q_lower for term in ("average", "avg", "mean")):
            met = metric_col or (numeric_cols[0] if numeric_cols else None)
            if met:
                met_alias = alias(met)
                dim = dimension_col
                if dim:
                    return (
                        f"SELECT {quote(dim)}, AVG({quote(met)}) AS avg_{met_alias} "
                        f"FROM {safe_table} "
                        f"GROUP BY {quote(dim)} "
                        f"LIMIT {limit};"
                    )
                return f"SELECT AVG({quote(met)}) AS avg_{met_alias} FROM {safe_table};"

        # 4. Count / Volume queries
        if any(term in q_lower for term in ("count", "how many", "number of")):
            dim = dimension_col or (categorical_cols[0] if categorical_cols else None)
            if dim:
                return (
                    f"SELECT {quote(dim)}, COUNT(*) AS total_count "
                    f"FROM {safe_table} "
                    f"GROUP BY {quote(dim)} "
                    f"ORDER BY total_count DESC "
                    f"LIMIT {limit};"
                )
            return f"SELECT COUNT(*) AS total_records FROM {safe_table};"

        # 5. General Grouping / Aggregation if dimension & metric found
        if dimension_col and metric_col:
            met_alias = alias(metric_col)
            return (
                f"SELECT {quote(dimension_col)}, SUM({quote(metric_col)}) AS total_{met_alias} "
                f"FROM {safe_table} "
                f"GROUP BY {quote(dimension_col)} "
                f"ORDER BY total_{met_alias} DESC "
                f"LIMIT {limit};"
            )

        # Default safe SELECT preview
        return f"SELECT * FROM {safe_table} LIMIT {limit};"

    @staticmethod
    def _clean_sql(sql: str) -> str:
        """Strip markdown fences, leading/trailing spaces, and excess semicolons."""
        cleaned = sql.strip()
        cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        if not cleaned.endswith(";"):
            cleaned += ";"
        return cleaned


__all__ = ["SQLGenerator"]
