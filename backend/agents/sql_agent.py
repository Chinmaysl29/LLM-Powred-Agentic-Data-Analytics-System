"""SQL Intelligence Agent Runner.

Translates natural language to secure SQL, validates against guardrails,
executes safely on active dataset storage or database, and provides structured results.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.agent_registry import BaseAgentRunner
from backend.app.services.data_retrieval_service import DataRetrievalService
from backend.sql_agent.sql_executor import SQLExecutor, SQLSandboxViolation
from backend.sql_agent.sql_generator import SQLGenerator
from backend.sql_agent.sql_guardrails import SQLGuardrails

logger = logging.getLogger(__name__)


class SQLAgentRunner(BaseAgentRunner):
    """Concrete runner for Text-to-SQL generation and safe execution in the Orchestrator pipeline."""

    def __init__(
        self,
        retrieval_service: DataRetrievalService | None = None,
        generator: SQLGenerator | None = None,
        guardrails: SQLGuardrails | None = None,
        executor: SQLExecutor | None = None,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._guardrails = guardrails or SQLGuardrails()
        self._generator = generator or SQLGenerator()
        self._executor = executor or SQLExecutor(guardrails=self._guardrails)

    @property
    def name(self) -> str:
        return "sql"

    async def run(self, context: WorkflowContext) -> dict[str, Any]:
        """Execute text-to-SQL generation and execution for workflow context."""
        query = context.query
        dataset_id = context.dataset_id

        # 1. Resolve table schema & DataFrame
        df: pd.DataFrame | None = None
        columns = context.metadata.get("column_names") or []
        column_types = context.metadata.get("column_types") or {}
        table_name = "active_dataset"

        if dataset_id and self._retrieval_service:
            try:
                df, _ = self._retrieval_service.load_dataframe(dataset_id=dataset_id)
                columns = list(df.columns)
                column_types = {c: str(df[c].dtype) for c in df.columns}
                table_name = f"dataset_{dataset_id.replace('-', '_')}"
            except Exception as e:
                logger.warning("Could not load DataFrame via retrieval service in SQLAgentRunner: %s", e)

        # Fallback to sample/context data if available
        if df is None:
            # Check if prior agent provided records or if context has preview
            if "retrieved_data" in context.results:
                records = context.results["retrieved_data"].get("records", [])
                if records:
                    df = pd.DataFrame(records)
                    columns = list(df.columns)
            elif "records" in context.metadata:
                df = pd.DataFrame(context.metadata["records"])
                columns = list(df.columns)

        # 2. Generate SQL
        try:
            generated_sql = self._generator.generate(
                query=query,
                table_name=table_name,
                columns=columns,
                column_types=column_types,
            )
        except Exception as e:
            logger.error("SQL generation error: %s", e)
            context.add_error("sql", f"Failed to generate SQL: {e}")
            return {
                "generated_sql": f"-- Error generating query: {e}",
                "execution_status": "generation_failed",
                "error": str(e),
                "columns": [],
                "rows": [],
            }

        # 3. Validate SQL against Guardrails
        eval_result = self._guardrails.evaluate_query(
            sql=generated_sql,
            allowed_tables=[table_name, "active_dataset", "dataset"],
        )
        if not eval_result.is_safe:
            violation_msg = "; ".join(eval_result.violations)
            logger.warning("SQL Guardrails rejected query: %s", violation_msg)
            context.add_error("sql", f"Guardrail blocked query: {violation_msg}")
            return {
                "generated_sql": generated_sql,
                "execution_status": "blocked_by_guardrails",
                "violations": eval_result.violations,
                "risk_level": eval_result.risk_level.value,
                "columns": [],
                "rows": [],
            }

        # 4. Execute Query
        if df is not None and not df.empty:
            try:
                exec_result = self._executor.execute_on_dataframe(
                    sql=generated_sql,
                    df=df,
                    table_name=table_name,
                )
                return {
                    "generated_sql": generated_sql,
                    "execution_status": "executed",
                    "execution_time_ms": exec_result.execution_time_ms,
                    "row_count": exec_result.row_count,
                    "columns": exec_result.columns,
                    "rows": exec_result.rows,
                    "is_truncated": exec_result.is_truncated,
                }
            except SQLSandboxViolation as e:
                return {
                    "generated_sql": generated_sql,
                    "execution_status": "sandbox_violation",
                    "error": str(e),
                    "columns": [],
                    "rows": [],
                }
            except Exception as e:
                logger.error("SQL execution error: %s", e)
                context.add_error("sql", f"Execution failed: {e}")
                return {
                    "generated_sql": generated_sql,
                    "execution_status": "execution_failed",
                    "error": str(e),
                    "columns": [],
                    "rows": [],
                }

        # If no DataFrame was available, return generated SQL with simulated status
        return {
            "generated_sql": generated_sql,
            "execution_status": "unexecuted_no_data",
            "columns": columns,
            "rows": [],
        }


__all__ = ["SQLAgentRunner"]
