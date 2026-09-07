"""Workflow Registry mapping user intents to deterministic, sequential agent pipelines.

Enforces:
Never hardcode logic. Future agents can be added easily.
"""

import logging
from backend.app.schemas.intent import IntentType

logger = logging.getLogger(__name__)


class WorkflowRegistry:
    """Extensible registry that determines which agents execute for each classified intent."""

    def __init__(self) -> None:
        self._workflows: dict[str, list[str]] = {}
        self._bootstrap_core_workflows()

    def register(self, intent: str, agents: list[str]) -> None:
        """Register or override a workflow for a given intent."""
        if not intent:
            raise ValueError("Intent cannot be empty")
        if not agents:
            raise ValueError("Workflow agents list cannot be empty")
        self._workflows[intent] = list(agents)
        logger.debug("Registered workflow for intent=%s: %s", intent, agents)

    def get_workflow(self, intent: str) -> list[str]:
        """Retrieve the ordered agent sequence for an intent."""
        if intent in self._workflows:
            return list(self._workflows[intent])
        logger.warning("No workflow registered for intent=%s; falling back to summary default", intent)
        return ["summary"]

    def has_workflow(self, intent: str) -> bool:
        """Check if a workflow is registered for an intent."""
        return intent in self._workflows

    def list_workflows(self) -> dict[str, list[str]]:
        """Return a copy of all registered intent-to-agent workflows."""
        return {k: list(v) for k, v in self._workflows.items()}

    def _bootstrap_core_workflows(self) -> None:
        """Initialize the standard workflows for all Phase 3.1 intents."""
        core_mappings = {
            IntentType.TREND_ANALYSIS.value: [
                "data_retrieval",
                "eda",
                "statistics",
                "summary",
            ],
            IntentType.EDA_ANALYSIS.value: [
                "data_retrieval",
                "eda",
                "statistics",
                "summary",
            ],
            IntentType.DATASET_OVERVIEW.value: [
                "data_retrieval",
                "eda",
                "summary",
            ],
            IntentType.COMPARISON_ANALYSIS.value: [
                "data_retrieval",
                "eda",
                "statistics",
                "visualization",
                "summary",
            ],
            IntentType.DISTRIBUTION_ANALYSIS.value: [
                "data_retrieval",
                "eda",
                "statistics",
                "visualization",
                "summary",
            ],
            IntentType.CORRELATION_ANALYSIS.value: [
                "data_retrieval",
                "eda",
                "statistics",
                "summary",
            ],
            IntentType.RANKING_ANALYSIS.value: [
                "data_retrieval",
                "eda",
                "statistics",
                "summary",
            ],
            IntentType.FORECASTING.value: [
                "data_retrieval",
                "statistics",
                "forecasting",
                "summary",
            ],
            IntentType.ANOMALY_DETECTION.value: [
                "data_retrieval",
                "eda",
                "statistics",
                "summary",
            ],
            IntentType.DASHBOARD_GENERATION.value: [
                "data_retrieval",
                "eda",
                "visualization",
                "summary",
            ],
            IntentType.REPORT_GENERATION.value: [
                "data_retrieval",
                "eda",
                "statistics",
                "recommendation",
                "summary",
            ],
            IntentType.RECOMMENDATION_GENERATION.value: [
                "data_retrieval",
                "eda",
                "recommendation",
                "summary",
            ],
            IntentType.WHAT_IF_ANALYSIS.value: [
                "data_retrieval",
                "statistics",
                "forecasting",
                "recommendation",
                "summary",
            ],
            IntentType.SQL_QUERY.value: [
                "data_retrieval",
                "sql",
                "summary",
            ],
            IntentType.RAG_QUERY.value: [
                "data_retrieval",
                "rag",
                "summary",
            ],
            IntentType.DATA_QUALITY.value: [
                "data_retrieval",
                "validation",
                "cleaning",
                "summary",
            ],
            IntentType.UNKNOWN.value: [
                "summary",
            ],
        }

        for intent, agents in core_mappings.items():
            self.register(intent, agents)
