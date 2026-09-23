"""Master orchestrator agent coordinating the multi-agent analysis pipeline.

Delegates execution to the Phase 3.2 OrchestratorService while maintaining
backward compatibility for existing agents and callers.
"""

import logging
from typing import Any

from backend.agents.intent_classifier import Intent, IntentClassifier
from backend.app.llm.provider import LLMProvider, get_llm_provider
from backend.app.schemas.orchestrator import OrchestratorResponse
from backend.app.services.orchestrator_service import OrchestratorService

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Coordinate intent classification, sequential agent execution, and response assembly."""

    def __init__(
        self,
        llm: LLMProvider | None = None,
        classifier: IntentClassifier | None = None,
        orchestrator_service: OrchestratorService | None = None,
    ) -> None:
        self._llm = llm or get_llm_provider()
        self._classifier = classifier or IntentClassifier(self._llm)
        self._service = orchestrator_service or OrchestratorService(
            intent_classifier=self._classifier.service,
            llm=self._llm,
        )

    @property
    def service(self) -> OrchestratorService:
        """Access the underlying OrchestratorService."""
        return self._service

    async def process_query(
        self,
        query: str,
        dataset_id: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process a user query through the full sequential orchestration pipeline."""
        orchestrator_res: OrchestratorResponse = await self._service.execute(
            query=query,
            dataset_id=dataset_id,
            context=context,
        )

        return {
            "response": orchestrator_res.summary,
            "intent": orchestrator_res.intent,
            "confidence": 0.95,
            "agent_result": orchestrator_res.results,
            "workflow": orchestrator_res.workflow,
            "executed_agents": orchestrator_res.executed_agents,
            "errors": orchestrator_res.errors,
            "execution_time_ms": orchestrator_res.execution_time_ms,
        }
