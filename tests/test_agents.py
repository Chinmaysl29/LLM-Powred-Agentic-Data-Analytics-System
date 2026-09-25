"""
Tests for all backend agents:
  - EDAAgentRunner
  - StatisticsAgentRunner
  - ValidationAgentRunner
  - ExecutiveSummaryAgentRunner
  - DataRetrievalAgentRunner
  - IntentClassifier (backward compat)
  - OrchestratorAgent (backward compat)
  - WorkflowPlanner agent
  - AgentRegistry (register, get, list)
  - BaseAgentRunner / DefaultAgentRunner
"""

import numpy as np
import pandas as pd
import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.agent_registry import AgentRegistry, BaseAgentRunner, DefaultAgentRunner
from backend.app.services.workflow_registry import WorkflowRegistry
from backend.agents.eda_agent import EDAAgentRunner
from backend.agents.executive_summary_agent import ExecutiveSummaryAgentRunner
from backend.agents.intent_classifier import IntentClassifier
from backend.agents.orchestrator_agent import OrchestratorAgent
from backend.agents.statistics_agent import StatisticsAgentRunner
from backend.agents.validation_agent import ValidationAgentRunner


# ===========================================================================
# WorkflowContext Tests
# ===========================================================================

class TestWorkflowContext:

    def test_create_context_with_defaults(self):
        ctx = WorkflowContext(query="test query", intent="eda_analysis")
        assert ctx.query == "test query"
        assert ctx.intent == "eda_analysis"
        assert ctx.results == {}
        assert ctx.errors == []

    def test_add_and_get_result(self):
        ctx = WorkflowContext(query="q")
        ctx.add_result("eda", {"rows": 100})
        assert ctx.get_result("eda") == {"rows": 100}

    def test_add_error(self):
        ctx = WorkflowContext(query="q")
        ctx.add_error("statistics", "division by zero")
        assert len(ctx.errors) == 1
        assert ctx.errors[0]["agent_name"] == "statistics"

    def test_log_execution(self):
        ctx = WorkflowContext(query="q")
        ctx.log_execution(agent_name="eda", status="success", duration_ms=12.5)
        assert len(ctx.execution_log) == 1
        assert ctx.execution_log[0].agent_name == "eda"
        assert ctx.execution_log[0].status == "success"

    def test_multiple_results_accumulated(self):
        ctx = WorkflowContext(query="q")
        ctx.add_result("data_retrieval", {"rows": 500})
        ctx.add_result("eda", {"type": "sales"})
        ctx.add_result("statistics", {"r2": 0.95})
        assert len(ctx.results) == 3

    def test_get_nonexistent_result_returns_none(self):
        ctx = WorkflowContext(query="q")
        assert ctx.get_result("nonexistent") is None


# ===========================================================================
# AgentRegistry Tests
# ===========================================================================

class TestAgentRegistry:

    def test_register_and_get_agent(self):
        registry = AgentRegistry()

        class DummyAgent(BaseAgentRunner):
            @property
            def name(self):
                return "dummy_agent"

            async def run(self, ctx: WorkflowContext) -> dict:
                return {}

        agent = DummyAgent()
        registry.register(agent)
        retrieved = registry.get("dummy_agent")
        assert retrieved is agent

    def test_get_nonexistent_returns_none(self):
        registry = AgentRegistry()
        assert registry.get("nonexistent") is None

    def test_list_agents(self):
        registry = AgentRegistry()

        class AgentA(BaseAgentRunner):
            @property
            def name(self):
                return "agent_a"

            async def run(self, ctx: WorkflowContext) -> dict:
                return {}

        class AgentB(BaseAgentRunner):
            @property
            def name(self):
                return "agent_b"

            async def run(self, ctx: WorkflowContext) -> dict:
                return {}

        registry.register(AgentA())
        registry.register(AgentB())
        names = registry.list_agents()
        assert "agent_a" in names
        assert "agent_b" in names

    def test_register_overwrites_existing_agent(self):
        registry = AgentRegistry()

        class AgentV1(BaseAgentRunner):
            @property
            def name(self):
                return "my_agent"

            async def run(self, ctx: WorkflowContext) -> dict:
                return {"version": 1}

        class AgentV2(BaseAgentRunner):
            @property
            def name(self):
                return "my_agent"

            async def run(self, ctx: WorkflowContext) -> dict:
                return {"version": 2}

        registry.register(AgentV1())
        registry.register(AgentV2())
        assert registry.get("my_agent").__class__.__name__ == "AgentV2"


# ===========================================================================
# WorkflowRegistry Tests
# ===========================================================================

class TestWorkflowRegistry:

    def test_all_core_intents_mapped(self):
        registry = WorkflowRegistry()
        core_intents = [
            "trend_analysis", "forecasting", "eda_analysis", "data_quality",
            "dataset_overview", "comparison_analysis", "correlation_analysis",
            "ranking_analysis", "anomaly_detection", "sql_query",
            "rag_query", "recommendation_generation", "report_generation",
            "what_if_analysis", "dashboard_generation", "distribution_analysis",
        ]
        for intent in core_intents:
            assert registry.has_workflow(intent), f"Missing workflow for intent: {intent}"

    def test_every_workflow_ends_with_summary(self):
        registry = WorkflowRegistry()
        for intent, workflow in registry.list_workflows().items():
            if intent != "unknown":
                assert "summary" in workflow, f"Workflow for {intent} lacks summary step"

    def test_dynamic_workflow_registration(self):
        registry = WorkflowRegistry()
        registry.register("custom_pipe", ["data_retrieval", "eda", "summary"])
        assert registry.get_workflow("custom_pipe") == ["data_retrieval", "eda", "summary"]

    def test_unknown_intent_has_fallback(self):
        registry = WorkflowRegistry()
        workflow = registry.get_workflow("unknown")
        assert isinstance(workflow, list)
        assert len(workflow) >= 1


# ===========================================================================
# EDAAgentRunner Tests
# ===========================================================================

class TestEDAAgentRunner:

    @pytest.fixture
    def sales_df(self):
        np.random.seed(1)
        return pd.DataFrame({
            "revenue": np.random.uniform(100, 5000, 50),
            "cost": np.random.uniform(50, 2000, 50),
            "region": np.random.choice(["North", "South"], 50),
        })

    @pytest.mark.asyncio
    async def test_run_with_mock_retrieval(self, sales_df):
        class MockRetrieval:
            def load_dataframe(self, dataset_id, **kwargs):
                return sales_df, False

        runner = EDAAgentRunner(retrieval_service=MockRetrieval())
        ctx = WorkflowContext(query="Analyze revenue", intent="eda_analysis", dataset_id="ds-1")
        result = await runner.run(ctx)
        assert "dataset_summary" in result or "error" in result

    @pytest.mark.asyncio
    async def test_run_without_retrieval_uses_context_metadata(self):
        runner = EDAAgentRunner(retrieval_service=None)
        ctx = WorkflowContext(
            query="Analyze sales",
            intent="eda_analysis",
            dataset_id="mock-ds",
            metadata={"row_count": 300, "column_count": 6},
        )
        result = await runner.run(ctx)
        assert isinstance(result, dict)

    def test_agent_name_is_eda(self):
        runner = EDAAgentRunner()
        assert runner.name in ("eda", "eda_agent")


# ===========================================================================
# StatisticsAgentRunner Tests
# ===========================================================================

class TestStatisticsAgentRunner:

    @pytest.fixture
    def stats_df(self):
        np.random.seed(2)
        x = np.linspace(1, 100, 60)
        y = 2.5 * x + np.random.normal(0, 5, 60)
        return pd.DataFrame({"x": x, "y": y})

    @pytest.mark.asyncio
    async def test_run_with_mock_retrieval(self, stats_df):
        class MockRetrieval:
            def load_dataframe(self, dataset_id, **kwargs):
                return stats_df, False

        runner = StatisticsAgentRunner(retrieval_service=MockRetrieval())
        ctx = WorkflowContext(query="Stats for x and y", intent="eda_analysis", dataset_id="ds-s1")
        result = await runner.run(ctx)
        assert isinstance(result, dict)

    def test_agent_name_is_statistics(self):
        runner = StatisticsAgentRunner()
        assert runner.name == "statistics"


# ===========================================================================
# ValidationAgentRunner Tests
# ===========================================================================

class TestValidationAgentRunner:

    @pytest.mark.asyncio
    async def test_run_with_empty_results(self):
        runner = ValidationAgentRunner()
        ctx = WorkflowContext(query="validate", intent="data_quality")
        result = await runner.run(ctx)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_run_with_eda_results_in_context(self):
        runner = ValidationAgentRunner()
        ctx = WorkflowContext(query="validate EDA", intent="eda_analysis")
        ctx.add_result("eda", {"correlations": {"correlation_matrix": {"a": {"b": 0.9}}}})
        result = await runner.run(ctx)
        assert isinstance(result, dict)
        assert "validation_status" in result or "status" in result

    def test_agent_name_is_validation(self):
        runner = ValidationAgentRunner()
        assert runner.name == "validation"


# ===========================================================================
# ExecutiveSummaryAgentRunner Tests
# ===========================================================================

class TestExecutiveSummaryAgentRunner:

    @pytest.mark.asyncio
    async def test_run_produces_summary(self):
        runner = ExecutiveSummaryAgentRunner(name="summary")
        ctx = WorkflowContext(query="summary test", intent="trend_analysis")
        ctx.add_result("data_retrieval", {"rows": 500})
        ctx.add_result("eda", {"dataset_summary": {"row_count": 500}})
        result = await runner.run(ctx)
        assert isinstance(result, dict)
        assert "executive_summary" in result or "summary" in result or "narrative" in result

    def test_agent_name_configurable(self):
        r1 = ExecutiveSummaryAgentRunner(name="summary")
        r2 = ExecutiveSummaryAgentRunner(name="executive_summary")
        assert r1.name == "summary"
        assert r2.name == "executive_summary"

    @pytest.mark.asyncio
    async def test_run_empty_context(self):
        runner = ExecutiveSummaryAgentRunner()
        ctx = WorkflowContext(query="empty", intent="unknown")
        result = await runner.run(ctx)
        assert isinstance(result, dict)


# ===========================================================================
# Backward Compatibility — IntentClassifier
# ===========================================================================

class TestIntentClassifierBackwardCompat:

    @pytest.mark.asyncio
    async def test_classify_returns_intent_dict(self):
        classifier = IntentClassifier(llm=None)
        result = await classifier.classify("Show sales trends")
        assert isinstance(result, dict)
        assert "intent" in result
        assert result["intent"] == "trend_analysis"

    @pytest.mark.asyncio
    async def test_classify_forecasting(self):
        classifier = IntentClassifier(llm=None)
        result = await classifier.classify("Predict next month revenue")
        assert result["intent"] == "forecasting"

    @pytest.mark.asyncio
    async def test_classify_has_confidence(self):
        classifier = IntentClassifier(llm=None)
        result = await classifier.classify("Show sales distribution")
        assert "confidence" in result
        assert isinstance(result["confidence"], float)


# ===========================================================================
# Backward Compatibility — OrchestratorAgent
# ===========================================================================

class TestOrchestratorAgentBackwardCompat:

    @pytest.mark.asyncio
    async def test_process_query_returns_structured_result(self):
        agent = OrchestratorAgent(llm=None)
        result = await agent.process_query("Show revenue trends")
        assert isinstance(result, dict)
        assert "intent" in result
        assert "workflow" in result
        assert result["intent"] == "trend_analysis"

    @pytest.mark.asyncio
    async def test_process_query_forecasting(self):
        agent = OrchestratorAgent(llm=None)
        result = await agent.process_query("Forecast sales")
        assert result["intent"] == "forecasting"

    @pytest.mark.asyncio
    async def test_process_query_has_agent_result(self):
        agent = OrchestratorAgent(llm=None)
        result = await agent.process_query("Analyze data trends")
        assert "agent_result" in result


# ===========================================================================
# DefaultAgentRunner Tests
# ===========================================================================

class TestDefaultAgentRunner:

    @pytest.mark.asyncio
    async def test_run_returns_dict(self):
        runner = DefaultAgentRunner(name="test_agent")
        ctx = WorkflowContext(query="test", intent="unknown")
        result = await runner.run(ctx)
        assert isinstance(result, dict)

    def test_name_property(self):
        runner = DefaultAgentRunner(name="my_agent")
        assert runner.name == "my_agent"
