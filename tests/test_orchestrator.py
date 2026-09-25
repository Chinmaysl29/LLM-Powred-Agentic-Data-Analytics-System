"""Comprehensive unit and integration tests for Phase 3.2 Orchestrator Agent."""

from typing import Any
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.exceptions import ValidationException
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.schemas.orchestrator import (
    OrchestratorRequest,
    OrchestratorResponse,
    WorkflowContext,
)
from backend.app.services.agent_registry import (
    AgentRegistry,
    BaseAgentRunner,
    DefaultAgentRunner,
)
from backend.app.services.intent_classification_service import IntentClassificationService
from backend.app.services.orchestrator_service import OrchestratorService
from backend.app.services.orchestrator_agent_service import OrchestratorAgentService
from backend.app.services.workflow_registry import WorkflowRegistry
from backend.agents.orchestrator_agent import OrchestratorAgent
from backend.orchestrator.context_manager import ContextManager
from backend.orchestrator.orchestrator import Orchestrator
from backend.orchestrator.task_router import TaskRouter
from backend.orchestrator.workflow_manager import WorkflowManager


@pytest.fixture
def in_memory_db() -> Session:
    """Isolated in-memory SQLite database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def workflow_registry() -> WorkflowRegistry:
    return WorkflowRegistry()


@pytest.fixture
def agent_registry() -> AgentRegistry:
    return AgentRegistry()


@pytest.fixture
def orchestrator_service(
    workflow_registry: WorkflowRegistry,
    agent_registry: AgentRegistry,
    in_memory_db: Session,
) -> OrchestratorService:
    intent_service = IntentClassificationService(llm=None)
    return OrchestratorService(
        intent_classifier=intent_service,
        workflow_registry=workflow_registry,
        agent_registry=agent_registry,
        llm=None,
        db=in_memory_db,
    )


@pytest.fixture
def api_client() -> TestClient:
    app = create_app()
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. Success Criterion: "Show sales trends"
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_success_criterion_sales_trends(orchestrator_service: OrchestratorService) -> None:
    """Input: 'Show sales trends'
    -> Intent: trend_analysis
    -> Workflow: data_retrieval -> eda -> statistics -> summary
    -> Aggregated Result returned with status 'success'.
    """
    response = await orchestrator_service.execute("Show sales trends")

    assert isinstance(response, OrchestratorResponse)
    assert response.intent == "trend_analysis"
    assert response.workflow == ["data_retrieval", "eda", "statistics", "summary"]
    assert response.executed_agents == ["data_retrieval", "eda", "statistics", "summary"]
    assert response.status == "success"
    assert len(response.errors) == 0
    assert response.execution_time_ms >= 0.0

    # Verify aggregated results domains
    results = response.results
    assert "data_retrieval" in results
    assert "analysis" in results
    assert "statistics" in results
    assert len(response.summary) > 0


# -----------------------------------------------------------------------------
# 2. Workflow Registry Coverage & Extensibility
# -----------------------------------------------------------------------------
def test_workflow_registry_all_intents_mapped(workflow_registry: WorkflowRegistry) -> None:
    """All 16 supported analytical intents + unknown are mapped in workflow registry."""
    intents = [
        "dataset_overview",
        "eda_analysis",
        "trend_analysis",
        "comparison_analysis",
        "distribution_analysis",
        "correlation_analysis",
        "ranking_analysis",
        "forecasting",
        "anomaly_detection",
        "dashboard_generation",
        "report_generation",
        "recommendation_generation",
        "what_if_analysis",
        "sql_query",
        "rag_query",
        "data_quality",
        "unknown",
    ]
    for intent in intents:
        assert workflow_registry.has_workflow(intent)
        workflow = workflow_registry.get_workflow(intent)
        assert isinstance(workflow, list)
        assert len(workflow) >= 1
        assert "summary" in workflow  # Every workflow terminates with executive synthesis


def test_workflow_registry_dynamic_registration(workflow_registry: WorkflowRegistry) -> None:
    """Custom workflows can be registered dynamically at runtime."""
    workflow_registry.register("custom_pipeline", ["data_retrieval", "validation", "summary"])
    assert workflow_registry.get_workflow("custom_pipeline") == ["data_retrieval", "validation", "summary"]


# -----------------------------------------------------------------------------
# 3. Shared Context Object Conformance
# -----------------------------------------------------------------------------
def test_shared_context_read_write_and_telemetry() -> None:
    """Shared context stores request_id, intent, workflow, results, errors, and telemetry."""
    context = WorkflowContext(
        query="Analyze churn",
        intent="eda_analysis",
        workflow=["data_retrieval", "eda", "summary"],
    )

    # Agents write to context
    context.add_result("data_retrieval", {"rows": 1000, "status": "loaded"})
    context.add_result("eda", {"missing_values": 5})

    # Agents read from context
    retrieval_data = context.get_result("data_retrieval")
    assert retrieval_data["rows"] == 1000

    # Error logging
    context.add_error("statistics", "Division by zero in variance")
    assert len(context.errors) == 1
    assert context.errors[0]["agent_name"] == "statistics"

    # Execution telemetry
    context.log_execution(agent_name="data_retrieval", status="success", duration_ms=12.5)
    assert len(context.execution_log) == 1
    assert context.execution_log[0].agent_name == "data_retrieval"
    assert context.execution_log[0].status == "success"


# -----------------------------------------------------------------------------
# 4. Sequential Execution Order & Agent Isolation
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_sequential_execution_order(orchestrator_service: OrchestratorService) -> None:
    """Orchestrator executes agents in strict sequential order without agent-to-agent communication."""
    execution_order = []

    class OrderTrackingRunner(BaseAgentRunner):
        def __init__(self, name: str) -> None:
            self._name = name

        @property
        def name(self) -> str:
            return self._name

        async def run(self, context: WorkflowContext) -> dict[str, Any]:
            execution_order.append(self._name)
            return {"step": len(execution_order), "prior": list(context.results.keys())}

    # Register custom tracking runners
    for name in ["data_retrieval", "eda", "statistics", "summary"]:
        orchestrator_service.agent_registry.register(OrderTrackingRunner(name))

    response = await orchestrator_service.execute("Show revenue trends")
    assert response.status == "success"
    assert execution_order == ["data_retrieval", "eda", "statistics", "summary"]


# -----------------------------------------------------------------------------
# 5. Error Handling & Partial Result Recovery
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_failure_recovers_with_partial_results(orchestrator_service: OrchestratorService) -> None:
    """When an agent fails, failure is logged, error is recorded, workflow continues, and partial results returned."""
    class FailingStatsRunner(BaseAgentRunner):
        @property
        def name(self) -> str:
            return "statistics"

        async def run(self, context: WorkflowContext) -> dict[str, Any]:
            raise RuntimeError("Out of memory calculating high-dimensional covariance")

    # Replace statistics agent with failing runner
    orchestrator_service.agent_registry.register(FailingStatsRunner())

    response = await orchestrator_service.execute("Show revenue trends")

    # Pipeline does NOT crash
    assert response.status == "partial_success"
    assert len(response.errors) == 1
    assert response.errors[0]["agent_name"] == "statistics"
    assert "Out of memory" in response.errors[0]["error"]

    # Other agents succeeded and partial results are present
    assert "data_retrieval" in response.executed_agents
    assert "eda" in response.executed_agents
    assert "summary" in response.executed_agents
    assert "statistics" not in response.executed_agents
    assert "data_retrieval" in response.results
    assert "analysis" in response.results


# -----------------------------------------------------------------------------
# 6. Extensible Architecture: Pluggable Custom Agent
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_extensible_agent_plug_in(orchestrator_service: OrchestratorService) -> None:
    """Future agents plug in without modifying orchestrator core."""
    class SentimentAnalysisAgent(BaseAgentRunner):
        @property
        def name(self) -> str:
            return "sentiment_agent"

        async def run(self, context: WorkflowContext) -> dict[str, Any]:
            return {
                "sentiment": "overwhelmingly_positive",
                "net_promoter_score": 78,
            }

    # Register custom agent and custom workflow
    orchestrator_service.agent_registry.register(SentimentAnalysisAgent())
    orchestrator_service.workflow_registry.register("customer_feedback", ["data_retrieval", "sentiment_agent", "summary"])

    # Directly execute with custom workflow
    custom_context = WorkflowContext(
        query="Analyze feedback",
        intent="customer_feedback",
        workflow=["data_retrieval", "sentiment_agent", "summary"],
    )
    
    response = await orchestrator_service.execute(
        query="Analyze customer feedback comments",
        context={"intent": "customer_feedback"},
    )

    assert "sentiment_agent" in response.executed_agents
    assert response.results["raw_agent_results"]["sentiment_agent"]["sentiment"] == "overwhelmingly_positive"


# -----------------------------------------------------------------------------
# 7. Dataset Context Enrichment
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dataset_context_enrichment(
    orchestrator_service: OrchestratorService,
    in_memory_db: Session,
) -> None:
    """When dataset_id is provided, metadata is attached to shared context for all agents to read."""
    # Seed dataset and metadata in database
    ds = Dataset(
        dataset_id="orch-ds-1",
        dataset_name="Sales Records",
        file_name="sales.csv",
        file_type="csv",
        file_path="/tmp/sales.csv",
        version=1,
        status="uploaded",
    )
    meta = DatasetMetadata(
        dataset_id="orch-ds-1",
        row_count=5000,
        column_count=4,
        column_names=["id", "date", "revenue", "region"],
        column_types={"id": "int", "date": "string", "revenue": "float", "region": "string"},
        columns_metadata=[],
        classifications={"numeric": ["id", "revenue"], "categorical": ["date", "region"]},
    )
    
    from backend.app.models.dataset_version import DatasetVersion
    v = DatasetVersion(
        version_id="orch-v-1",
        dataset_id="orch-ds-1",
        version_number=1,
        storage_path="/tmp/sales.csv",
        change_type="initial_upload",
        metadata_snapshot={},
        quality_snapshot={},
        created_by="test_user",
        is_active=True
    )
    
    in_memory_db.add(ds)
    in_memory_db.add(meta)
    in_memory_db.add(v)
    in_memory_db.commit()

    response = await orchestrator_service.execute(
        query="Analyze sales trends over time",
        dataset_id="orch-ds-1",
    )

    assert response.status == "success"
    assert response.dataset_id == "orch-ds-1"
    # data_retrieval agent picked up rows from context.metadata
    assert response.results["data_retrieval"]["rows"] == 5000


# -----------------------------------------------------------------------------
# 8. Checklist Aliases & Backward Compatibility Bridges
# -----------------------------------------------------------------------------
def test_checklist_alias_compatibility() -> None:
    """OrchestratorAgentService matches OrchestratorService."""
    assert OrchestratorAgentService is OrchestratorService


def test_orchestrator_module_bridges() -> None:
    """backend.orchestrator components match implementations."""
    assert Orchestrator is OrchestratorService
    assert ContextManager is WorkflowContext
    assert WorkflowManager is WorkflowRegistry
    assert TaskRouter is AgentRegistry


@pytest.mark.asyncio
async def test_agents_orchestrator_agent_backward_compatibility() -> None:
    """backend.agents.orchestrator_agent.OrchestratorAgent works with process_query."""
    agent = OrchestratorAgent(llm=None)
    result = await agent.process_query("Show sales trends")

    assert isinstance(result, dict)
    assert result["intent"] == "trend_analysis"
    assert "agent_result" in result
    assert "workflow" in result
    assert result["workflow"] == ["data_retrieval", "eda", "statistics", "summary"]


# -----------------------------------------------------------------------------
# 9. API Endpoint Integration Tests
# -----------------------------------------------------------------------------
def test_api_execute_orchestrator(api_client: TestClient) -> None:
    """POST /api/v1/orchestrator/execute successfully orchestrates a user query."""
    response = api_client.post(
        "/api/v1/orchestrator/execute",
        json={"query": "Show revenue trends"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "trend_analysis"
    assert data["status"] == "success"
    assert data["workflow"] == ["data_retrieval", "eda", "statistics", "summary"]
    assert "analysis" in data["results"]
    assert "statistics" in data["results"]


def test_api_list_workflows(api_client: TestClient) -> None:
    """GET /api/v1/orchestrator/workflows returns all intent workflows."""
    response = api_client.get("/api/v1/orchestrator/workflows")
    assert response.status_code == 200
    data = response.json()
    assert "trend_analysis" in data
    assert "forecasting" in data
    assert "data_quality" in data


def test_api_execute_validation_error(api_client: TestClient) -> None:
    """POST /api/v1/orchestrator/execute rejects empty query with 422."""
    response = api_client.post(
        "/api/v1/orchestrator/execute",
        json={"query": ""},
    )
    assert response.status_code == 422
