"""Create a trace span for each inbound request using its request ID."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from backend.monitoring.tracing import tracer


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
        with tracer.start_span(f"{request.method} {request.url.path}", trace_id=trace_id):
            return await call_next(request)
