"""Response timing middleware."""

from time import perf_counter

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """Expose processing duration in a response header."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started_at = perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time-Ms"] = f"{(perf_counter() - started_at) * 1000:.2f}"
        return response
