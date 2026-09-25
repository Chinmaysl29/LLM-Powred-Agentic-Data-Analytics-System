"""
Tests for forecasting API endpoints:
  POST /api/v1/forecasting/prepare-data
  POST /api/v1/forecasting/validate
  POST /api/v1/forecasting/prophet
  POST /api/v1/forecasting/arima
  POST /api/v1/forecasting/xgboost
  POST /api/v1/forecasting/validate-forecast
  POST /api/v1/forecasting/scenarios
  POST /api/v1/forecasting/what-if
  POST /api/v1/forecasting/agent-select
  GET  /api/v1/forecasting/runs/{run_id}
"""

import numpy as np
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.app.main import create_app


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _monthly_records(n=36, start="2021-01-01"):
    base = datetime.strptime(start, "%Y-%m-%d")
    np.random.seed(1)
    values = np.linspace(1000, 5000, n) + np.random.normal(0, 100, n)
    return [
        {
            "date": (base + timedelta(days=30 * i)).strftime("%Y-%m-%d"),
            "value": float(max(v, 1.0)),
        }
        for i, v in enumerate(values)
    ]



def _forecast_payload(n=36, horizon=6, target="revenue", frequency="monthly"):
    return {
        "series": _monthly_records(n),
        "target": target,
        "horizon": horizon,
        "frequency": frequency,
    }


# ===========================================================================
# Prepare Data Tests
# ===========================================================================

class TestPrepareDataEndpoint:

    def test_prepare_data_returns_200(self, client):
        payload = {
            "records": [{"date": r["date"], "value": r["value"]} for r in _monthly_records(36)],
            "config": {"time_column": "date", "target_column": "value"},
        }
        res = client.post("/api/v1/forecasting/prepare-data", json=payload)
        assert res.status_code == 200

    def test_prepare_data_validation_report_present(self, client):
        payload = {
            "records": [{"date": r["date"], "value": r["value"]} for r in _monthly_records(36)],
            "config": {},
        }
        res = client.post("/api/v1/forecasting/prepare-data", json=payload)
        data = res.json()
        assert "validation_report" in data

    def test_prepare_data_empty_records_returns_400(self, client):
        res = client.post("/api/v1/forecasting/prepare-data", json={"records": [], "config": {}})
        assert res.status_code == 400


# ===========================================================================
# Validate Endpoint Tests
# ===========================================================================

class TestValidateForcastDataEndpoint:

    def test_validate_valid_records_returns_200(self, client):
        payload = {
            "records": [{"date": r["date"], "value": r["value"]} for r in _monthly_records(36)],
            "time_column": "date",
            "target_column": "value",
            "frequency": "monthly",
        }
        res = client.post("/api/v1/forecasting/validate", json=payload)
        assert res.status_code == 200

    def test_validate_returns_is_valid_field(self, client):
        payload = {
            "records": [{"date": r["date"], "value": r["value"]} for r in _monthly_records(36)],
            "time_column": "date",
            "target_column": "value",
        }
        data = client.post("/api/v1/forecasting/validate", json=payload).json()
        assert "is_valid" in data

    def test_validate_no_records_no_dataset_returns_400(self, client):
        res = client.post("/api/v1/forecasting/validate", json={"frequency": "monthly"})
        assert res.status_code == 400


# ===========================================================================
# ARIMA Forecast Endpoint Tests
# ===========================================================================

class TestARIMAEndpoint:

    def test_arima_returns_200(self, client):
        res = client.post("/api/v1/forecasting/arima", json=_forecast_payload(36, 6))
        assert res.status_code == 200

    def test_arima_returns_forecast_values(self, client):
        data = client.post("/api/v1/forecasting/arima", json=_forecast_payload(36, 6)).json()
        assert "forecast_values" in data
        assert len(data["forecast_values"]) == 6

    def test_arima_model_name_contains_arima(self, client):
        data = client.post("/api/v1/forecasting/arima", json=_forecast_payload(36, 3)).json()
        assert "arima" in data.get("model_name", "").lower()

    def test_arima_has_forecast_id(self, client):
        data = client.post("/api/v1/forecasting/arima", json=_forecast_payload(36, 3)).json()
        assert "forecast_id" in data


# ===========================================================================
# Prophet Forecast Endpoint Tests
# ===========================================================================

class TestProphetEndpoint:

    def test_prophet_returns_200(self, client):
        res = client.post("/api/v1/forecasting/prophet", json=_forecast_payload(36, 6))
        assert res.status_code == 200

    def test_prophet_returns_forecast_values(self, client):
        data = client.post("/api/v1/forecasting/prophet", json=_forecast_payload(36, 6)).json()
        assert "forecast_values" in data
        assert len(data["forecast_values"]) == 6

    def test_prophet_model_name(self, client):
        data = client.post("/api/v1/forecasting/prophet", json=_forecast_payload(36, 3)).json()
        assert "prophet" in data.get("model_name", "").lower()


# ===========================================================================
# XGBoost Forecast Endpoint Tests
# ===========================================================================

class TestXGBoostEndpoint:

    def test_xgboost_returns_200(self, client):
        res = client.post("/api/v1/forecasting/xgboost", json=_forecast_payload(36, 6))
        assert res.status_code == 200

    def test_xgboost_returns_forecast_values(self, client):
        data = client.post("/api/v1/forecasting/xgboost", json=_forecast_payload(36, 6)).json()
        assert "forecast_values" in data
        assert len(data["forecast_values"]) == 6


# ===========================================================================
# What-If Analysis Endpoint Tests
# ===========================================================================

class TestWhatIfEndpoint:

    def test_what_if_returns_200(self, client):
        payload = {**_forecast_payload(36, 6), "what_if_query": "marketing +15%"}
        res = client.post("/api/v1/forecasting/what-if", json=payload)
        assert res.status_code == 200

    def test_what_if_returns_analysis_result(self, client):
        payload = {**_forecast_payload(36, 3), "what_if_query": "revenue +10%"}
        data = client.post("/api/v1/forecasting/what-if", json=payload).json()
        assert data is not None


# ===========================================================================
# Agent Select Endpoint Tests
# ===========================================================================

class TestAgentSelectEndpoint:

    def test_agent_select_returns_200(self, client):
        res = client.post("/api/v1/forecasting/agent-select", json=_forecast_payload(36, 6))
        assert res.status_code == 200

    def test_agent_select_returns_selected_model(self, client):
        data = client.post("/api/v1/forecasting/agent-select", json=_forecast_payload(36, 3)).json()
        assert "selected_model" in data or "model_name" in data


# ===========================================================================
# Forecast Runs Endpoint Tests
# ===========================================================================

class TestForecastRunsEndpoint:

    def test_get_nonexistent_run_returns_404(self, client):
        from unittest.mock import AsyncMock
        from backend.app.database.postgres import PostgresDatabase, get_db_session
        from backend.app.database.redis import RedisCache
        from backend.app.database.chromadb import ChromaDatabase

        app = create_app()
        # Need DB for this test
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from backend.app.models.base import Base

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        SessionFactory = sessionmaker(bind=engine)

        def override_db():
            s = SessionFactory()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db_session] = override_db

        with TestClient(app) as c:
            res = c.get("/api/v1/forecasting/runs/nonexistent-run-id-xyz")
        assert res.status_code == 404
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.clear()
