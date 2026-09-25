"""Comprehensive unit and integration tests for Phase 3.3 Workflow Planner."""

from typing import Any
import pytest
from fastapi.testclient import TestClient

from backend.app.core.exceptions import ValidationException
from backend.app.main import create_app
from backend.app.schemas.planner import (
    PlanDependency,
    WorkflowPlan,
    WorkflowPlanningRequest,
)
from backend.app.services.agent_registry import AgentRegistry
from backend.app.services.intent_classification_service import IntentClassificationService
from backend.app.services.orchestrator_service import OrchestratorService
from backend.app.services.planner_service import PlannerService
from backend.app.services.workflow_planner_service import (
    DependencyEngine,
    OptimizationLayer,
    RulesEngine,
    WorkflowPlannerService,
)
from backend.app.services.workflow_registry import WorkflowRegistry
from backend.agents.workflow_planner import WorkflowPlanner


@pytest.fixture
def workflow_registry() -> WorkflowRegistry:
    return WorkflowRegistry()


@pytest.fixture
def planner_service(workflow_registry: WorkflowRegistry) -> WorkflowPlannerService:
    intent_service = IntentClassificationService(llm=None)
    return WorkflowPlannerService(
        intent_classifier=intent_service,
        workflow_registry=workflow_registry,
        llm=None,
    )


@pytest.fixture
def api_client() -> TestClient:
    app = create_app()
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. Success Criterion: Composite Sales Analysis + Prediction Goal
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_success_criterion_sales_analysis_and_prediction(
    planner_service: WorkflowPlannerService,
) -> None:
    """Input: 'Analyze my sales dataset and predict next quarter revenue'
    Output workflow: ['data_retrieval', 'eda', 'statistics', 'forecasting', 'summary'].
    """
    request = WorkflowPlanningRequest(
        query="Analyze my sales dataset and predict next quarter revenue",
    )
    plan = await planner_service.plan(request)

    assert isinstance(plan, WorkflowPlan)
    assert plan.steps == ["data_retrieval", "eda", "statistics", "forecasting", "summary"]
    assert plan.workflow == ["data_retrieval", "eda", "statistics", "forecasting", "summary"]
    assert plan.workflow_type == "dynamic"
    assert any("Composite goal" in r for r in plan.rules_triggered)
    assert plan.estimated_execution_time > 0.0


# -----------------------------------------------------------------------------
# 2. Revenue Drivers / Driver Analysis Goal
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_driver_analysis_workflow_planning(
    planner_service: WorkflowPlannerService,
) -> None:
    """Input: 'Find revenue drivers'
    Output workflow includes data_retrieval, eda, correlation, recommendation, summary.
    """
    request = WorkflowPlanningRequest(
        query="Find revenue drivers",
    )
    plan = await planner_service.plan(request)

    assert "data_retrieval" in plan.steps
    assert "eda" in plan.steps
    assert "correlation" in plan.steps
    assert "recommendation" in plan.steps
    assert "summary" in plan.steps
    assert any("Driver analysis" in r for r in plan.rules_triggered)


# -----------------------------------------------------------------------------
# 3. Dependency Engine Enforces Topological Prerequisites
# -----------------------------------------------------------------------------
def test_dependency_engine_prerequisite_injection() -> None:
    """If forecasting is requested alone, dependency engine injects data_retrieval and statistics."""
    engine = DependencyEngine()
    resolved = engine.resolve_and_order(["forecasting", "summary"])

    assert resolved[0] == "data_retrieval"
    assert resolved.index("statistics") < resolved.index("forecasting")
    assert resolved[-1] == "summary"

    deps = engine.build_dependencies(resolved)
    forecasting_dep = next(d for d in deps if d.step == "forecasting")
    assert "statistics" in forecasting_dep.requires
    assert "data_retrieval" in forecasting_dep.requires


# -----------------------------------------------------------------------------
# 4. Rules Engine: Temporal Guard for Forecasting
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_temporal_guard_skips_forecasting_when_no_time_columns(
    planner_service: WorkflowPlannerService,
) -> None:
    """Forecasting is omitted when metadata indicates dataset has no temporal/datetime columns."""
    metadata_no_time = {
        "column_names": ["customer_id", "age", "gender", "annual_spend"],
        "column_types": {"customer_id": "int", "age": "int", "gender": "string", "annual_spend": "float"},
        "classifications": {"numeric": ["age", "annual_spend"], "categorical": ["gender"], "datetime": []},
        "row_count": 500,
    }
    request = WorkflowPlanningRequest(
        query="Predict future sales",
        intent="forecasting",
        metadata=metadata_no_time,
    )
    plan = await planner_service.plan(request)

    # Forecasting step was safely removed because no temporal columns exist
    assert "forecasting" not in plan.steps
    assert "eda" in plan.steps
    assert any("No datetime columns" in r for r in plan.rules_triggered)


@pytest.mark.asyncio
async def test_temporal_guard_retains_forecasting_when_time_columns_exist(
    planner_service: WorkflowPlannerService,
) -> None:
    """Forecasting is retained when datetime column exists in metadata."""
    metadata_with_time = {
        "column_names": ["order_date", "revenue"],
        "column_types": {"order_date": "datetime64", "revenue": "float"},
        "classifications": {"numeric": ["revenue"], "datetime": ["order_date"]},
        "row_count": 500,
    }
    request = WorkflowPlanningRequest(
        query="Predict future sales",
        intent="forecasting",
        metadata=metadata_with_time,
    )
    plan = await planner_service.plan(request)

    assert "forecasting" in plan.steps
    assert "statistics" in plan.steps


# -----------------------------------------------------------------------------
# 5. Rules Engine: Low Quality Score Remediation
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_quality_remediation_injects_validation_and_cleaning(
    planner_service: WorkflowPlannerService,
) -> None:
    """When dataset quality score is below 60.0, validation and cleaning steps are automatically injected."""
    request = WorkflowPlanningRequest(
        query="Show sales trends",
        quality={"overall_score": 45.0, "completeness_score": 40.0},
    )
    plan = await planner_service.plan(request)

    assert "validation" in plan.steps
    assert "cleaning" in plan.steps
    assert plan.steps.index("validation") < plan.steps.index("cleaning")
    assert any("Low quality score" in r for r in plan.rules_triggered)


# -----------------------------------------------------------------------------
# 6. Optimization Layer: Large Dataset Sampling & Deduplication
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_large_dataset_sampling_optimization(
    planner_service: WorkflowPlannerService,
) -> None:
    """Datasets exceeding 1M rows automatically enable sampling optimization."""
    request = WorkflowPlanningRequest(
        query="Show revenue trends",
        metadata={"row_count": 3_500_000, "column_names": ["date", "revenue"]},
    )
    plan = await planner_service.plan(request)

    assert plan.use_sampling is True
    assert any("sampling optimization" in opt for opt in plan.optimizations_applied)


def test_optimization_layer_deduplication() -> None:
    """Duplicate steps are removed while preserving order."""
    raw_steps = ["data_retrieval", "eda", "statistics", "eda", "statistics", "summary"]
    deduped = OptimizationLayer.deduplicate(raw_steps)
    assert deduped == ["data_retrieval", "eda", "statistics", "summary"]


# -----------------------------------------------------------------------------
# 7. Workflow Output Schema Conformance
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workflow_output_schema(planner_service: WorkflowPlannerService) -> None:
    """Output conforms to { workflow_id, intent, workflow_type, steps, dependencies, estimated_execution_time }."""
    request = WorkflowPlanningRequest(query="Explore customer demographics")
    plan = await planner_service.plan(request)

    data = plan.model_dump()
    assert "workflow_id" in data
    assert data["workflow_id"].startswith("wf_")
    assert "intent" in data
    assert "workflow_type" in data
    assert isinstance(data["steps"], list)
    assert isinstance(data["dependencies"], list)
    assert isinstance(data["estimated_execution_time"], float)
    assert data["estimated_execution_time"] > 0.0


# -----------------------------------------------------------------------------
# 8. Checklist Aliases & Module Bridges
# -----------------------------------------------------------------------------
def test_checklist_alias_compatibility() -> None:
    """PlannerService and WorkflowPlanner match WorkflowPlannerService."""
    assert PlannerService is WorkflowPlannerService
    assert WorkflowPlanner is WorkflowPlannerService


# -----------------------------------------------------------------------------
# 9. Orchestrator Integration with Dynamic Workflow Planning
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_orchestrator_executes_dynamic_planned_workflow() -> None:
    """Orchestrator integrates with WorkflowPlanner to dynamically plan and execute."""
    intent_service = IntentClassificationService(llm=None)
    workflow_registry = WorkflowRegistry()
    agent_registry = AgentRegistry()
    planner = WorkflowPlannerService(intent_classifier=intent_service, workflow_registry=workflow_registry)

    orchestrator = OrchestratorService(
        intent_classifier=intent_service,
        workflow_registry=workflow_registry,
        agent_registry=agent_registry,
        planner=planner,
    )

    # Trigger with dynamic planning flag
    response = await orchestrator.execute(
        query="Analyze my sales dataset and predict next quarter revenue",
        dynamic_planning=True,
    )

    assert response.status == "success"
    # Orchestrator executed the dynamically planned composite workflow
    assert response.workflow == ["data_retrieval", "eda", "statistics", "forecasting", "summary"]
    assert response.executed_agents == ["data_retrieval", "eda", "statistics", "forecasting", "summary"]


# -----------------------------------------------------------------------------
# 10. API Route Integration Tests
# -----------------------------------------------------------------------------
def test_api_generate_workflow_plan(api_client: TestClient) -> None:
    """POST /api/v1/planner/plan generates a valid execution plan."""
    response = api_client.post(
        "/api/v1/planner/plan",
        json={"query": "Analyze my sales dataset and predict next quarter revenue"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "workflow_id" in data
    assert data["steps"] == ["data_retrieval", "eda", "statistics", "forecasting", "summary"]
    assert len(data["dependencies"]) > 0
    assert data["estimated_execution_time"] > 0


def test_api_list_templates(api_client: TestClient) -> None:
    """GET /api/v1/planner/templates returns all baseline templates."""
    response = api_client.get("/api/v1/planner/templates")
    assert response.status_code == 200
    data = response.json()
    assert "eda_analysis" in data
    assert "forecasting" in data
    assert "trend_analysis" in data


def test_api_planner_validation_error(api_client: TestClient) -> None:
    """POST /api/v1/planner/plan rejects empty query with 422."""
    response = api_client.post(
        "/api/v1/planner/plan",
        json={"query": ""},
    )
    assert response.status_code == 422
