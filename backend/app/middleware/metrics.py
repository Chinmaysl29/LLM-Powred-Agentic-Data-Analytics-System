"""HTTP instrumentation middleware for the Prometheus metrics endpoint."""

from time import perf_counter

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from backend.monitoring.prometheus_metrics import platform_metrics


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started_at = perf_counter()
        response = await call_next(request)
        route = getattr(request.scope.get("route"), "path", request.url.path)
        platform_metrics.observe_request(
            request.method,
            route,
            response.status_code,
            perf_counter() - started_at,
        )
        return response
