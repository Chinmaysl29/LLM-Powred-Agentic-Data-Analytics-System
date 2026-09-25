"""Comprehensive unit and integration tests for Phase 3.1 Intent Classifier."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.core.exceptions import ValidationException
from backend.app.schemas.intent import (
    IntentClassificationRequest,
    IntentClassificationResponse,
    IntentDefinition,
    IntentType,
)
from backend.app.services.intent_classification_service import (
    IntentClassificationService,
    IntentRegistry,
    get_intent_classification_service,
)
from backend.app.services.intent_service import IntentService
from backend.agents.intent_classifier import Intent, IntentClassifier
from backend.orchestrator.intent_classifier import IntentClassifier as OrchestratorIntentClassifier


@pytest.fixture
def registry() -> IntentRegistry:
    """Return a fresh IntentRegistry with core intents initialized."""
    return IntentRegistry()


@pytest.fixture
def intent_service(registry: IntentRegistry) -> IntentClassificationService:
    """Return an IntentClassificationService using deterministic heuristics (no LLM)."""
    return IntentClassificationService(llm=None, registry=registry)


@pytest.fixture
def api_client() -> TestClient:
    """FastAPI TestClient for API endpoint integration."""
    app = create_app()
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. Success Criteria Explicit Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_success_criterion_revenue_trends(intent_service: IntentClassificationService) -> None:
    """User asks: 'Show revenue trends' -> Returns: trend_analysis."""
    result = await intent_service.classify("Show revenue trends")
    assert result.intent == IntentType.TREND_ANALYSIS.value
    assert result.confidence >= 0.90
    assert "trend_analysis" in result.required_agents
    assert len(result.reasoning) > 0


@pytest.mark.asyncio
async def test_success_criterion_predict_sales(intent_service: IntentClassificationService) -> None:
    """User asks: 'Predict sales for next quarter' -> Returns: forecasting."""
    result = await intent_service.classify("Predict sales for next quarter")
    assert result.intent == IntentType.FORECASTING.value
    assert result.confidence >= 0.90
    assert "forecasting" in result.required_agents
    assert "data_retrieval" in result.required_agents
    assert len(result.reasoning) > 0


@pytest.mark.asyncio
async def test_success_criterion_find_duplicates(intent_service: IntentClassificationService) -> None:
    """User asks: 'Find duplicate records' -> Returns: data_quality."""
    result = await intent_service.classify("Find duplicate records")
    assert result.intent == IntentType.DATA_QUALITY.value
    assert result.confidence >= 0.90
    assert "data_quality" in result.required_agents
    assert len(result.reasoning) > 0


@pytest.mark.asyncio
async def test_ranking_analysis_highest_revenue(intent_service: IntentClassificationService) -> None:
    """User asks: 'Which product generated the highest revenue?' -> Returns: ranking_analysis."""
    result = await intent_service.classify("Which product generated the highest revenue?")
    assert result.intent == IntentType.RANKING_ANALYSIS.value
    assert result.confidence >= 0.90
    assert "ranking_analysis" in result.required_agents
    assert len(result.reasoning) > 0


# -----------------------------------------------------------------------------
# 2. Supported Intent Coverage Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query,expected_intent",
    [
        ("Show me a summary of this dataset", IntentType.DATASET_OVERVIEW.value),
        ("Perform exploratory analysis on customer churn", IntentType.EDA_ANALYSIS.value),
        ("Analyze sales trends over time", IntentType.TREND_ANALYSIS.value),
        ("Compare Q1 sales with Q2 sales", IntentType.COMPARISON_ANALYSIS.value),
        ("Show the distribution of customer age", IntentType.DISTRIBUTION_ANALYSIS.value),
        ("Is there a correlation between marketing spend and revenue?", IntentType.CORRELATION_ANALYSIS.value),
        ("Show the top 5 customers by sales", IntentType.RANKING_ANALYSIS.value),
        ("Forecast revenue for the next 6 months", IntentType.FORECASTING.value),
        ("Find outliers in transaction amounts", IntentType.ANOMALY_DETECTION.value),
        ("Create a dashboard for executive KPIs", IntentType.DASHBOARD_GENERATION.value),
        ("Generate a monthly executive summary report", IntentType.REPORT_GENERATION.value),
        ("What recommendations do you have to reduce churn?", IntentType.RECOMMENDATION_GENERATION.value),
        ("What if we increase prices by 10% next quarter?", IntentType.WHAT_IF_ANALYSIS.value),
        ("SELECT * FROM orders WHERE total > 100", IntentType.SQL_QUERY.value),
        ("Search documentation for metric calculation rules", IntentType.RAG_QUERY.value),
        ("Check data quality and missing values", IntentType.DATA_QUALITY.value),
        ("Hello, how are you today?", IntentType.UNKNOWN.value),
    ],
)
async def test_all_supported_intents(
    intent_service: IntentClassificationService,
    query: str,
    expected_intent: str,
) -> None:
    """Verify each supported intent category is correctly resolved."""
    result = await intent_service.classify(query)
    assert result.intent == expected_intent
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.required_agents, list)
    assert len(result.reasoning) > 0


# -----------------------------------------------------------------------------
# 3. Output Schema Conformance
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_output_schema_structure(intent_service: IntentClassificationService) -> None:
    """Every classification returns intent, confidence, reasoning, and required_agents."""
    result = await intent_service.classify("Predict sales for next quarter")

    # Pydantic validation
    assert isinstance(result, IntentClassificationResponse)

    # Dict serialization matching required output schema
    data = result.model_dump()
    assert set(data.keys()) == {"intent", "confidence", "reasoning", "required_agents"}
    assert data["intent"] == "forecasting"
    assert data["confidence"] >= 0.90
    assert isinstance(data["required_agents"], list)
    assert "data_retrieval" in data["required_agents"]
    assert "forecasting" in data["required_agents"]


# -----------------------------------------------------------------------------
# 4. Extensible Intent Registry Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_extensible_intent_registry(registry: IntentRegistry) -> None:
    """Custom intents can be registered dynamically at runtime and resolved."""
    custom_intent = IntentDefinition(
        name="churn_risk_modeling",
        description="Predict and score customer churn risk using ML models",
        required_agents=["data_retrieval", "churn_modeler", "retention_agent"],
        keywords=["churn risk", "retention risk"],
        patterns=[r"\b(churn risk|customer retention risk)\b"],
        examples=["Assess customer churn risk"],
    )
    registry.register(custom_intent)

    service = IntentClassificationService(llm=None, registry=registry)
    result = await service.classify("Assess customer churn risk for the current accounts")

    assert result.intent == "churn_risk_modeling"
    assert result.confidence >= 0.90
    assert result.required_agents == ["data_retrieval", "churn_modeler", "retention_agent"]


# -----------------------------------------------------------------------------
# 5. Input Validation Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_query_validation_empty_string(intent_service: IntentClassificationService) -> None:
    """Empty queries raise a ValidationException."""
    with pytest.raises(ValidationException):
        await intent_service.classify("")


@pytest.mark.asyncio
async def test_query_validation_whitespace(intent_service: IntentClassificationService) -> None:
    """Whitespace-only queries raise a ValidationException."""
    with pytest.raises(ValidationException):
        await intent_service.classify("    ")


@pytest.mark.asyncio
async def test_query_validation_too_long(intent_service: IntentClassificationService) -> None:
    """Queries exceeding 2000 characters raise a ValidationException."""
    long_query = "word " * 500
    with pytest.raises(ValidationException):
        await intent_service.classify(long_query)


# -----------------------------------------------------------------------------
# 6. LLM Integration & Offline Fallback Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_llm_classification_success() -> None:
    """When LLM is available and returns valid JSON, LLM output is used."""
    mock_llm = MagicMock()
    mock_llm.chat_with_json = AsyncMock(
        return_value='{"intent": "what_if_analysis", "confidence": 0.93, "reasoning": "User asks a hypothetical simulation question."}'
    )

    service = IntentClassificationService(llm=mock_llm)
    result = await service.classify("What happens to margin if discount is 15%?")

    assert result.intent == IntentType.WHAT_IF_ANALYSIS.value
    assert result.confidence == 0.93
    assert "what_if_analysis" in result.required_agents
    mock_llm.chat_with_json.assert_awaited_once()


@pytest.mark.asyncio
async def test_llm_failure_falls_back_gracefully() -> None:
    """When LLM call fails, system gracefully falls back to heuristic matching without crashing."""
    mock_llm = MagicMock()
    mock_llm.chat_with_json = AsyncMock(side_effect=RuntimeError("Groq API connection timeout"))

    service = IntentClassificationService(llm=mock_llm)
    # This query has strong heuristic pattern
    result = await service.classify("Show revenue trends")

    assert result.intent == IntentType.TREND_ANALYSIS.value
    assert result.confidence >= 0.90
    assert "trend_analysis" in result.required_agents


# -----------------------------------------------------------------------------
# 7. Checklist Aliases & Backward Compatibility
# -----------------------------------------------------------------------------
def test_checklist_alias_compatibility() -> None:
    """IntentService matches IntentClassificationService."""
    assert IntentService is IntentClassificationService


@pytest.mark.asyncio
async def test_agents_intent_classifier_backward_compatibility() -> None:
    """backend.agents.intent_classifier provides backward-compatible Intent and IntentClassifier."""
    classifier = IntentClassifier(llm=None)
    result = await classifier.classify("Show revenue trends")

    assert isinstance(result, dict)
    assert result["intent"] == "trend_analysis"
    assert result["confidence"] >= 0.90
    assert isinstance(result["required_agents"], list)

    # Orchestrator agent alias verification
    orch_classifier = OrchestratorIntentClassifier(llm=None)
    orch_result = await orch_classifier.classify("Find duplicate records")
    assert orch_result["intent"] == "data_quality"


# -----------------------------------------------------------------------------
# 8. API Route Integration Test
# -----------------------------------------------------------------------------
def test_intent_classification_api_endpoint(api_client: TestClient) -> None:
    """POST /api/v1/intent/classify successfully returns structured intent."""
    response = api_client.post(
        "/api/v1/intent/classify",
        json={"query": "Show revenue trends"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "trend_analysis"
    assert data["confidence"] >= 0.90
    assert "trend_analysis" in data["required_agents"]
    assert len(data["reasoning"]) > 0


def test_intent_classification_api_validation_error(api_client: TestClient) -> None:
    """POST /api/v1/intent/classify rejects empty query with 422 Unprocessable Entity."""
    response = api_client.post(
        "/api/v1/intent/classify",
        json={"query": ""},
    )
    assert response.status_code == 422
