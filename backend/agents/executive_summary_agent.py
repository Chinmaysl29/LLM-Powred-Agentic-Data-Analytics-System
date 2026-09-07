"""Executive Summary Agent implementation.

Concrete runner synthesizing technical analytics across all upstream agents
(Data Retrieval, EDA, Statistics, Quality, and Validation) into executive-ready
business narratives, multi-tier summaries, health scores, and prioritized actions.
"""

import logging
from typing import Any

from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.agent_registry import BaseAgentRunner
from backend.app.services.executive_summary_service import ExecutiveSummaryService

logger = logging.getLogger(__name__)


class ExecutiveSummaryAgentRunner(BaseAgentRunner):
    """Concrete runner for the Executive Summary Agent in the Orchestrator pipeline."""

    def __init__(
        self,
        summary_service: ExecutiveSummaryService | None = None,
        name: str = "summary",
    ) -> None:
        self._summary_service = summary_service or ExecutiveSummaryService()
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: WorkflowContext) -> dict[str, Any]:
        """Execute executive summary synthesis across all accumulated findings in context."""
        logger.info(
            "ExecutiveSummaryAgentRunner (%s) executing for request_id=%s across %d prior results",
            self._name,
            context.request_id,
            len(context.results),
        )

        try:
            summary_result = self._summary_service.generate_summary(
                results=context.results,
                metadata=context.metadata if context.metadata else None,
                profile=context.profile if context.profile else None,
                quality=context.quality if context.quality else None,
                query=context.query,
            )
            data = summary_result.model_dump(mode="json")
            # Store under both standard keys in context for cross-agent accessibility
            context.add_result("summary", data)
            context.add_result("executive_summary", data)
            return data
        except Exception as exc:
            logger.error("ExecutiveSummaryAgentRunner encountered error: %s", exc, exc_info=True)
            raise
