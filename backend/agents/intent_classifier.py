"""Agent intent classifier bridge.

Provides Intent and IntentClassifier wrapping the Phase 3.1
IntentClassificationService for backward compatibility and multi-agent coordination.
"""

import logging
from enum import Enum
from typing import Any

from backend.app.llm.provider import LLMProvider, get_llm_provider
from backend.app.schemas.intent import (
    IntentClassificationResponse,
    IntentType,
)
from backend.app.services.intent_classification_service import (
    IntentClassificationService,
    IntentRegistry,
)

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """Recognized user intent categories with Phase 3.1 taxonomy and legacy aliases."""

    # Phase 3.1 Supported Intents
    DATASET_OVERVIEW = "dataset_overview"
    EDA_ANALYSIS = "eda_analysis"
    TREND_ANALYSIS = "trend_analysis"
    COMPARISON_ANALYSIS = "comparison_analysis"
    DISTRIBUTION_ANALYSIS = "distribution_analysis"
    CORRELATION_ANALYSIS = "correlation_analysis"
    RANKING_ANALYSIS = "ranking_analysis"
    FORECASTING = "forecasting"
    ANOMALY_DETECTION = "anomaly_detection"
    DASHBOARD_GENERATION = "dashboard_generation"
    REPORT_GENERATION = "report_generation"
    RECOMMENDATION_GENERATION = "recommendation_generation"
    WHAT_IF_ANALYSIS = "what_if_analysis"
    SQL_QUERY = "sql_query"
    RAG_QUERY = "rag_query"
    DATA_QUALITY = "data_quality"
    UNKNOWN = "unknown"

    # Legacy Aliases
    EDA = "eda"
    FORECAST = "forecast"
    VISUALIZATION = "visualization"
    RECOMMENDATION = "recommendation"
    DATA_CLEANING = "data_cleaning"
    STATISTICS = "statistics"
    REPORT = "report"
    UPLOAD = "upload"
    GENERAL_CHAT = "general_chat"


class IntentClassifier:
    """Classify user queries into intent categories using the Phase 3.1 service."""

    def __init__(
        self,
        llm: LLMProvider | None = None,
        registry: IntentRegistry | None = None,
    ) -> None:
        self._service = IntentClassificationService(llm=llm, registry=registry)

    @property
    def service(self) -> IntentClassificationService:
        return self._service

    async def classify(self, query: str, context: Any = None) -> dict[str, Any]:
        """Classify a user query and return dictionary matching the output schema."""
        parsed_context = {"context": context} if isinstance(context, str) else context
        result = await self._service.classify(query=query, context=parsed_context)
        return {
            "intent": result.intent,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "required_agents": result.required_agents,
        }

    async def classify_structured(self, query: str, context: Any = None) -> IntentClassificationResponse:
        """Classify a user query and return validated Pydantic model."""
        parsed_context = {"context": context} if isinstance(context, str) else context
        return await self._service.classify(query=query, context=parsed_context)
