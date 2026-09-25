"""
Tests for analytics API endpoints:
  POST /api/v1/intent/classify
  POST /api/v1/orchestrator/execute
  GET  /api/v1/orchestrator/workflows
  POST /api/v1/planner/plan
  GET  /api/v1/planner/templates
  GET  /api/v1/eda/{dataset_id}
  GET  /api/v1/statistics/{dataset_id}
  POST /api/v1/validation/validate
  POST /api/v1/validation/validate-sql
  POST /api/v1/summary/generate
  GET  /api/v1/summary/{dataset_id}
  POST /api/v1/sql/guardrails/check
  POST /api/v1/sql/guardrails/sanitize
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.eda_service import EDAService, get_eda_service
from backend.app.services.statistics_service import StatisticsService, get_statistics_service


# ===========================================================================
# Fixture: TestClient with no infra needed (services mocked via overrides)
# ===========================================================================

@pytest.fixture(scope="function")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def sales_df():
    np.random.seed(7)
    n = 60
    return pd.DataFrame({
        "revenue": np.random.uniform(1000, 9000, n),
        "cost": np.random.uniform(500, 4000, n),
        "region": np.random.choice(["North", "South"], n),
    })


# ===========================================================================
# Intent Classification Endpoint Tests
# ===========================================================================

class TestIntentEndpoint:

    def test_classify_trend_analysis(self, client):
        res = client.post("/api/v1/intent/classify", json={"query": "Show revenue trends"})
        assert res.status_code == 200
        assert res.json()["intent"] == "trend_analysis"

    def test_classify_forecasting(self, client):
        res = client.post("/api/v1/intent/classify", json={"query": "Predict sales for next quarter"})
        assert res.status_code == 200
        assert res.json()["intent"] == "forecasting"

    def test_classify_data_quality(self, client):
        res = client.post("/api/v1/intent/classify", json={"query": "Find duplicate records"})
        assert res.status_code == 200
        assert res.json()["intent"] == "data_quality"

    def test_classify_returns_confidence(self, client):
        res = client.post("/api/v1/intent/classify", json={"query": "Show sales trends"})
        data = res.json()
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0

    def test_classify_returns_required_agents(self, client):
        res = client.post("/api/v1/intent/classify", json={"query": "Show sales trends"})
        assert "required_agents" in res.json()

    def test_classify_returns_reasoning(self, client):
        res = client.post("/api/v1/intent/classify", json={"query": "Show sales trends"})
        assert "reasoning" in res.json()
        assert len(res.json()["reasoning"]) > 0

    def test_classify_empty_query_returns_422(self, client):
        res = client.post("/api/v1/intent/classify", json={"query": ""})
        assert res.status_code == 422

    def test_classify_missing_query_returns_422(self, client):
        res = client.post("/api/v1/intent/classify", json={})
        assert res.status_code == 422

    def test_classify_with_dataset_id_context(self, client):
        res = client.post("/api/v1/intent/classify", json={
            "query": "Analyze this dataset",
            "dataset_id": "ds-123",
        })
        assert res.status_code == 200

    def test_classify_sql_query(self, client):
        res = client.post("/api/v1/intent/classify", json={
            "query": "SELECT * FROM orders WHERE amount > 100"
        })
        assert res.json()["intent"] == "sql_query"


# ===========================================================================
# Orchestrator Endpoint Tests
# ===========================================================================

class TestOrchestratorEndpoint:

    def test_execute_returns_200(self, client):
        res = client.post("/api/v1/orchestrator/execute", json={"query": "Show revenue trends"})
        assert res.status_code == 200

    def test_execute_returns_intent(self, client):
        data = client.post("/api/v1/orchestrator/execute", json={"query": "Show revenue trends"}).json()
        assert data["intent"] == "trend_analysis"

    def test_execute_returns_success_status(self, client):
        data = client.post("/api/v1/orchestrator/execute", json={"query": "Show revenue trends"}).json()
        assert data["status"] == "success"

    def test_execute_returns_workflow(self, client):
        data = client.post("/api/v1/orchestrator/execute", json={"query": "Show trends"}).json()
        assert "workflow" in data
        assert isinstance(data["workflow"], list)

    def test_execute_returns_executed_agents(self, client):
        data = client.post("/api/v1/orchestrator/execute", json={"query": "Show trends"}).json()
        assert "executed_agents" in data

    def test_execute_returns_execution_time(self, client):
        data = client.post("/api/v1/orchestrator/execute", json={"query": "Analyze data"}).json()
        assert "execution_time_ms" in data
        assert data["execution_time_ms"] >= 0

    def test_execute_empty_query_returns_422(self, client):
        res = client.post("/api/v1/orchestrator/execute", json={"query": ""})
        assert res.status_code == 422

    def test_execute_with_dataset_id(self, client):
        data = client.post("/api/v1/orchestrator/execute", json={
            "query": "Analyze dataset",
            "dataset_id": "test-ds-id",
        }).json()
        assert data["dataset_id"] == "test-ds-id"

    def test_list_workflows_returns_200(self, client):
        res = client.get("/api/v1/orchestrator/workflows")
        assert res.status_code == 200

    def test_list_workflows_contains_all_intents(self, client):
        data = client.get("/api/v1/orchestrator/workflows").json()
        assert "trend_analysis" in data
        assert "forecasting" in data
        assert "data_quality" in data


# ===========================================================================
# Planner Endpoint Tests
# ===========================================================================

class TestPlannerEndpoint:

    def test_plan_returns_200(self, client):
        res = client.post("/api/v1/planner/plan", json={
            "query": "Analyze sales trends",
            "intent": "trend_analysis",
        })
        assert res.status_code == 200

    def test_plan_returns_steps(self, client):
        data = client.post("/api/v1/planner/plan", json={
            "query": "Analyze sales",
            "intent": "trend_analysis",
        }).json()
        assert "steps" in data
        assert isinstance(data["steps"], list)
        assert len(data["steps"]) >= 1

    def test_plan_includes_summary_step(self, client):
        data = client.post("/api/v1/planner/plan", json={
            "query": "Revenue overview",
            "intent": "eda_analysis",
        }).json()
        assert "summary" in data["steps"]

    def test_list_templates_returns_200(self, client):
        res = client.get("/api/v1/planner/templates")
        assert res.status_code == 200

    def test_list_templates_returns_dict(self, client):
        data = client.get("/api/v1/planner/templates").json()
        assert isinstance(data, dict)
        assert len(data) > 0


# ===========================================================================
# EDA Endpoint Tests
# ===========================================================================

class TestEDAEndpoint:

    def test_eda_analysis_returns_200_with_mocked_service(self, sales_df):
        app = create_app()

        class MockEDAService:
            async def analyze_dataset(self, dataset_id, **kwargs):
                svc = EDAService()
                return svc.analyze_dataframe(sales_df, dataset_id=dataset_id)

        app.dependency_overrides[get_eda_service] = lambda: MockEDAService()
        with TestClient(app) as c:
            res = c.get("/api/v1/eda/test-ds-1")
        assert res.status_code == 200
        app.dependency_overrides.clear()

    def test_eda_returns_dataset_id(self, sales_df):
        app = create_app()

        class MockEDAService:
            async def analyze_dataset(self, dataset_id, **kwargs):
                svc = EDAService()
                return svc.analyze_dataframe(sales_df, dataset_id=dataset_id)

        app.dependency_overrides[get_eda_service] = lambda: MockEDAService()
        with TestClient(app) as c:
            data = c.get("/api/v1/eda/my-dataset").json()
        assert data["dataset_id"] == "my-dataset"
        app.dependency_overrides.clear()

    def test_eda_returns_status_success(self, sales_df):
        app = create_app()

        class MockEDAService:
            async def analyze_dataset(self, dataset_id, **kwargs):
                svc = EDAService()
                return svc.analyze_dataframe(sales_df, dataset_id=dataset_id)

        app.dependency_overrides[get_eda_service] = lambda: MockEDAService()
        with TestClient(app) as c:
            data = c.get("/api/v1/eda/ds-test").json()
        assert data["status"] == "success"
        app.dependency_overrides.clear()


# ===========================================================================
# Statistics Endpoint Tests
# ===========================================================================

class TestStatisticsEndpoint:

    def test_statistics_returns_200_with_mocked_service(self, sales_df):
        app = create_app()

        class MockStatisticsService:
            async def analyze_dataset(self, dataset_id, **kwargs):
                svc = StatisticsService()
                return svc.analyze_dataframe(sales_df, dataset_id=dataset_id)

        app.dependency_overrides[get_statistics_service] = lambda: MockStatisticsService()
        with TestClient(app) as c:
            res = c.get("/api/v1/statistics/test-ds")
        assert res.status_code == 200
        app.dependency_overrides.clear()

    def test_statistics_returns_status_success(self, sales_df):
        app = create_app()

        class MockStatisticsService:
            async def analyze_dataset(self, dataset_id, **kwargs):
                svc = StatisticsService()
                return svc.analyze_dataframe(sales_df, dataset_id=dataset_id)

        app.dependency_overrides[get_statistics_service] = lambda: MockStatisticsService()
        with TestClient(app) as c:
            data = c.get("/api/v1/statistics/ds-test").json()
        assert data["status"] == "success"
        app.dependency_overrides.clear()


# ===========================================================================
# Validation Endpoint Tests
# ===========================================================================

class TestValidationEndpoint:

    def test_validate_empty_results_passes(self, client):
        res = client.post("/api/v1/validation/validate", json={
            "results": {},
            "query": "Validate nothing",
        })
        assert res.status_code == 200

    def test_validate_returns_validation_status(self, client):
        data = client.post("/api/v1/validation/validate", json={"results": {}}).json()
        assert "validation_result" in data
        assert "validation_status" in data["validation_result"]

    def test_validate_sql_safe_query(self, client):
        res = client.post("/api/v1/validation/validate-sql", json={
            "sql": "SELECT * FROM orders",
        })
        assert res.status_code == 200
        assert res.json()["is_safe"] is True

    def test_validate_sql_dangerous_query(self, client):
        res = client.post("/api/v1/validation/validate-sql", json={
            "sql": "DROP TABLE users",
        })
        assert res.status_code == 200
        assert res.json()["is_safe"] is False


# ===========================================================================
# SQL Guardrails Endpoint Tests
# ===========================================================================

class TestSQLGuardrailsEndpoint:

    def test_check_safe_query_returns_200(self, client):
        res = client.post("/api/v1/sql/guardrails/check", json={"sql": "SELECT * FROM orders LIMIT 100"})
        assert res.status_code == 200

    def test_check_safe_query_is_safe_true(self, client):
        data = client.post("/api/v1/sql/guardrails/check", json={"sql": "SELECT id FROM users"}).json()
        assert data["guardrail_result"]["is_safe"] is True

    def test_check_dangerous_query_is_safe_false(self, client):
        data = client.post("/api/v1/sql/guardrails/check", json={"sql": "DROP TABLE orders"}).json()
        assert data["guardrail_result"]["is_safe"] is False

    def test_sanitize_query_returns_200(self, client):
        res = client.post("/api/v1/sql/guardrails/sanitize", json={"sql": "SELECT * FROM orders;"})
        assert res.status_code == 200

    def test_sanitize_returns_sanitized_sql(self, client):
        data = client.post("/api/v1/sql/guardrails/sanitize", json={"sql": "SELECT * FROM orders;"}).json()
        assert "sanitized_sql" in data
        assert "original_sql" in data

    def test_check_with_allowed_tables(self, client):
        data = client.post("/api/v1/sql/guardrails/check", json={
            "sql": "SELECT * FROM sales",
            "allowed_tables": ["sales", "orders"],
        }).json()
        assert data["guardrail_result"]["is_safe"] is True
