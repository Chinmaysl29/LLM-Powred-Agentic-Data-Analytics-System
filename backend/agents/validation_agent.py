"""Validation Agent implementation.

Concrete runner and analytical gatekeeper ensuring data grounding,
mathematical consistency, schema compliance, cross-agent alignment,
safe SQL operations, chart suitability, and enterprise auditability.
"""

import logging
from typing import Any

from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.agent_registry import BaseAgentRunner
from backend.app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)


class ValidationAgentRunner(BaseAgentRunner):
    """Concrete runner for the Validation Agent in the Orchestrator pipeline."""

    def __init__(self, validation_service: ValidationService | None = None) -> None:
        self._validation_service = validation_service or ValidationService()

    @property
    def name(self) -> str:
        return "validation"

    async def run(self, context: WorkflowContext) -> dict[str, Any]:
        """Execute validation suite across all accumulated agent results in context."""
        logger.info(
            "ValidationAgentRunner executing for request_id=%s across %d prior results",
            context.request_id, len(context.results)
        )

        try:
            val_result = self._validation_service.validate_results(
                results=context.results,
                context=context,
                query=context.query,
            )
            return val_result.model_dump(mode="json")
        except Exception as exc:
            logger.error("ValidationAgentRunner encountered unhandled error: %s", exc, exc_info=True)
            raise
