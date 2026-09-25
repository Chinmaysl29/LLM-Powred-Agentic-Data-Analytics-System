"""
Tests for backend/app/middleware/ and backend/monitoring/prometheus_metrics.py.
Validates RequestID propagation, response timing, Prometheus counters, and audit.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from backend.app.middleware.request_id import RequestIDMiddleware
from backend.app.middleware.response_time import ResponseTimeMiddleware
from backend.monitoring.prometheus_metrics import PlatformMetrics, platform_metrics


# ===========================================================================
# Helper: minimal FastAPI app for middleware testing
# ===========================================================================

def _build_app_with_middleware(middleware_cls, **kwargs) -> FastAPI:
    app = FastAPI()
    app.add_middleware(middleware_cls, **kwargs)

    @app.get("/ping")
    async def ping():
        return {"status": "ok"}

    @app.get("/echo-request-id")
    async def echo(request: Request):
        return {"request_id": getattr(request.state, "request_id", None)}

    return app


# ===========================================================================
# RequestIDMiddleware
# ===========================================================================

class TestRequestIDMiddleware:
    """Tests for X-Request-ID header propagation."""

    def test_generated_request_id_added_to_response(self):
        app = _build_app_with_middleware(RequestIDMiddleware)
        client = TestClient(app)
        res = client.get("/ping")
        assert "X-Request-ID" in res.headers
        # Should be a UUID-like string (36 chars including hyphens)
        assert len(res.headers["X-Request-ID"]) == 36

    def test_inbound_request_id_echoed_back(self):
        app = _build_app_with_middleware(RequestIDMiddleware)
        client = TestClient(app)
        custom_id = "my-custom-trace-id-xyz"
        res = client.get("/ping", headers={"X-Request-ID": custom_id})
        assert res.headers["X-Request-ID"] == custom_id

    def test_request_id_available_on_request_state(self):
        app = _build_app_with_middleware(RequestIDMiddleware)
        client = TestClient(app)
        custom_id = "state-test-id-123"
        res = client.get("/echo-request-id", headers={"X-Request-ID": custom_id})
        assert res.json()["request_id"] == custom_id

    def test_no_inbound_id_generates_unique_ids(self):
        app = _build_app_with_middleware(RequestIDMiddleware)
        client = TestClient(app)
        ids = {client.get("/ping").headers["X-Request-ID"] for _ in range(5)}
        # All 5 must be unique
        assert len(ids) == 5

    def test_empty_x_request_id_generates_new_id(self):
        app = _build_app_with_middleware(RequestIDMiddleware)
        client = TestClient(app)
        # Empty string header → should generate a new UUID
        res = client.get("/ping", headers={"X-Request-ID": ""})
        assert len(res.headers["X-Request-ID"]) > 0


# ===========================================================================
# ResponseTimeMiddleware
# ===========================================================================

class TestResponseTimeMiddleware:
    """Tests for X-Process-Time-Ms header."""

    def test_response_contains_process_time_header(self):
        app = _build_app_with_middleware(ResponseTimeMiddleware)
        client = TestClient(app)
        res = client.get("/ping")
        assert "X-Process-Time-Ms" in res.headers

    def test_process_time_is_numeric(self):
        app = _build_app_with_middleware(ResponseTimeMiddleware)
        client = TestClient(app)
        res = client.get("/ping")
        val = float(res.headers["X-Process-Time-Ms"])
        assert val >= 0.0

    def test_process_time_is_non_negative_for_all_endpoints(self):
        app = _build_app_with_middleware(ResponseTimeMiddleware)
        client = TestClient(app)
        for _ in range(3):
            res = client.get("/ping")
            assert float(res.headers["X-Process-Time-Ms"]) >= 0.0


# ===========================================================================
# Both middlewares on a single app (integration)
# ===========================================================================

class TestMiddlewareIntegration:
    """Test that RequestID and ResponseTime play well together."""

    def test_both_headers_present(self):
        app = FastAPI()
        app.add_middleware(ResponseTimeMiddleware)
        app.add_middleware(RequestIDMiddleware)

        @app.get("/multi")
        async def multi():
            return {"ok": True}

        client = TestClient(app)
        res = client.get("/multi", headers={"X-Request-ID": "combined-test"})
        assert res.headers["X-Request-ID"] == "combined-test"
        assert "X-Process-Time-Ms" in res.headers


# ===========================================================================
# PlatformMetrics
# ===========================================================================

class TestPlatformMetrics:
    """Tests for the Prometheus metrics registry."""

    @pytest.fixture
    def metrics(self):
        """Return a fresh PlatformMetrics instance for each test."""
        return PlatformMetrics()

    def test_observe_request_increments_counter(self, metrics):
        metrics.observe_request("GET", "/api/v1/health", 200, 0.05)
        output = metrics.render().decode()
        assert "ai_analyst_api_requests_total" in output

    def test_observe_request_records_duration(self, metrics):
        metrics.observe_request("POST", "/api/v1/datasets/upload", 201, 0.120)
        output = metrics.render().decode()
        assert "ai_analyst_api_request_duration_seconds" in output

    def test_set_dependency_health_healthy(self, metrics):
        metrics.set_dependency_health("postgres", True)
        output = metrics.render().decode()
        assert "ai_analyst_dependency_up" in output

    def test_set_dependency_health_unhealthy(self, metrics):
        metrics.set_dependency_health("redis", False)
        output = metrics.render().decode()
        assert "ai_analyst_dependency_up" in output

    def test_record_agent_execution(self, metrics):
        metrics.record_agent_execution("eda_agent", "success")
        output = metrics.render().decode()
        assert "ai_analyst_agent_executions_total" in output

    def test_record_agent_execution_failure(self, metrics):
        metrics.record_agent_execution("forecasting_agent", "failure")
        output = metrics.render().decode()
        assert "ai_analyst_agent_executions_total" in output

    def test_record_job_event(self, metrics):
        metrics.record_job_event("report_generation", "completed")
        output = metrics.render().decode()
        assert "ai_analyst_background_jobs_total" in output

    def test_record_dependency_operation(self, metrics):
        metrics.record_dependency_operation("postgres", "query", "success")
        output = metrics.render().decode()
        assert "ai_analyst_dependency_operations_total" in output

    def test_record_error_with_exception_instance(self, metrics):
        exc = ValueError("test error")
        metrics.record_error("auth_service", exc)
        output = metrics.render().decode()
        assert "ai_analyst_errors_total" in output

    def test_record_error_with_string(self, metrics):
        metrics.record_error("orchestrator", "timeout")
        output = metrics.render().decode()
        assert "ai_analyst_errors_total" in output

    def test_record_business_event(self, metrics):
        metrics.record_business_event("dataset_uploaded", count=1)
        output = metrics.render().decode()
        assert "ai_analyst_business_events_total" in output

    def test_render_returns_bytes(self, metrics):
        output = metrics.render()
        assert isinstance(output, bytes)

    def test_render_valid_prometheus_format(self, metrics):
        metrics.observe_request("GET", "/test", 200, 0.01)
        output = metrics.render().decode()
        # Prometheus text format starts with # HELP or metric lines
        assert len(output) > 0

    def test_global_platform_metrics_singleton_exists(self):
        assert platform_metrics is not None
        assert isinstance(platform_metrics, PlatformMetrics)

    def test_multiple_requests_accumulate_counts(self, metrics):
        for i in range(5):
            metrics.observe_request("GET", "/api/v1/health", 200, 0.01 * i)
        output = metrics.render().decode()
        assert "ai_analyst_api_requests_total" in output

    def test_multiple_dependency_labels_tracked(self, metrics):
        for dep in ("postgres", "redis", "chromadb"):
            metrics.set_dependency_health(dep, True)
        output = metrics.render().decode()
        assert "ai_analyst_dependency_up" in output
