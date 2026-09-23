"""Prometheus metrics registry shared by the API and background services."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


class PlatformMetrics:
    """Low-cardinality metrics for API, infrastructure, and agent operations."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.api_requests = Counter(
            "ai_analyst_api_requests_total",
            "Completed API requests",
            ("method", "route", "status"),
            registry=self.registry,
        )
        self.api_duration = Histogram(
            "ai_analyst_api_request_duration_seconds",
            "API request duration",
            ("method", "route"),
            registry=self.registry,
        )
        self.dependency_up = Gauge(
            "ai_analyst_dependency_up",
            "Dependency health (1 healthy, 0 unhealthy)",
            ("dependency",),
            registry=self.registry,
        )
        self.agent_executions = Counter(
            "ai_analyst_agent_executions_total",
            "Agent executions by agent and outcome",
            ("agent", "outcome"),
            registry=self.registry,
        )
        self.job_events = Counter(
            "ai_analyst_background_jobs_total",
            "Background job state transitions",
            ("job_type", "status"),
            registry=self.registry,
        )
        self.dependency_operations = Counter(
            "ai_analyst_dependency_operations_total",
            "Database and Redis operations by outcome",
            ("dependency", "operation", "outcome"),
            registry=self.registry,
        )
        self.errors = Counter(
            "ai_analyst_errors_total",
            "Application errors by component and type",
            ("component", "error_type"),
            registry=self.registry,
        )
        self.business_events = Counter(
            "ai_analyst_business_events_total",
            "Business events by event type",
            ("event_type",),
            registry=self.registry,
        )

    def observe_request(self, method: str, route: str, status_code: int, duration_seconds: float) -> None:
        labels = {"method": method, "route": route, "status": str(status_code)}
        self.api_requests.labels(**labels).inc()
        self.api_duration.labels(method=method, route=route).observe(duration_seconds)

    def set_dependency_health(self, dependency: str, healthy: bool) -> None:
        self.dependency_up.labels(dependency=dependency).set(1 if healthy else 0)

    def record_agent_execution(self, agent: str, outcome: str) -> None:
        self.agent_executions.labels(agent=agent, outcome=outcome).inc()

    def record_job_event(self, job_type: str, status: str) -> None:
        self.job_events.labels(job_type=job_type, status=status).inc()

    def record_dependency_operation(self, dependency: str, operation: str, outcome: str = "success") -> None:
        self.dependency_operations.labels(dependency=dependency, operation=operation, outcome=outcome).inc()

    def record_error(self, component: str, error: Exception | str) -> None:
        error_type = type(error).__name__ if isinstance(error, Exception) else str(error)
        self.errors.labels(component=component, error_type=error_type[:80]).inc()

    def record_business_event(self, event_type: str, count: int = 1) -> None:
        self.business_events.labels(event_type=event_type).inc(count)

    def render(self) -> bytes:
        return generate_latest(self.registry)


platform_metrics = PlatformMetrics()
