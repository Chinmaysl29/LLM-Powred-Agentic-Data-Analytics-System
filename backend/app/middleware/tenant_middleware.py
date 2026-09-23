"""Tenant middleware for extracting and injecting tenant identity into request state."""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware extracting tenant context from JWT `tid` claim or headers and binding to `request.state`."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        settings = get_settings()
        extracted_tenant_id: str | None = None

        # 1. Attempt extraction from JWT Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                from jose import jwt
                # Decode claims without signature verification in middleware;
                # cryptographic authentication verification remains in auth dependency
                claims = jwt.get_unverified_claims(token)
                extracted_tenant_id = claims.get("tid") or claims.get("tenant_id")
                if extracted_tenant_id:
                    logger.debug("Extracted tenant_id=%s from JWT tid claim", extracted_tenant_id)
            except Exception as exc:
                logger.warning("Could not parse JWT token in tenant middleware: %s", exc)

        # 2. Fallback to custom HTTP header if present
        if not extracted_tenant_id:
            header_tid = request.headers.get("X-Tenant-ID", "").strip()
            if header_tid:
                extracted_tenant_id = header_tid
                logger.debug("Extracted tenant_id=%s from X-Tenant-ID header", extracted_tenant_id)

        # 3. Default fallback to system tenant for backward compatibility & health endpoints
        final_tenant_id = extracted_tenant_id or getattr(settings, "default_tenant_id", "system")
        request.state.tenant_id = final_tenant_id

        # Propagate through downstream request chain
        response = await call_next(request)
        # Expose response header for tenant tracing
        response.headers["X-Tenant-ID"] = final_tenant_id
        return response
