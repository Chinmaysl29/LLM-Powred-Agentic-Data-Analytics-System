"""Structured audit logger backed by the Phase 16.5 audit service."""

from __future__ import annotations

import logging
from typing import Any

from backend.app.services.audit_trail_service import audit_trail_service

logger = logging.getLogger(__name__)


class AuditLogger:
    """Compatibility façade that persists structured events when a session is supplied."""

    def log_event(self, *, actor_id: str, action: str, resource_type: str, resource_id: str | None = None,
                  actor_type: str = "user", status: str = "success", metadata: dict[str, Any] | None = None,
                  request_id: str | None = None, **context: Any) -> dict[str, Any]:
        event = audit_trail_service.record(actor=actor_id, actor_type=actor_type, action=action,
            resource_type=resource_type, resource_id=resource_id, status=status, metadata=metadata or context,
            details=context, request_id=request_id)
        logger.info("audit_event event_id=%s action=%s resource_type=%s status=%s", event["event_id"], action, resource_type, status)
        return event


audit_logger = AuditLogger()
