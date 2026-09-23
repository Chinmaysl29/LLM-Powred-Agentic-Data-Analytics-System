"""Audit trail persistence service with a resilient in-memory fallback."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.audit_entry import AuditEntry
from backend.app.repositories.audit_repository import AuditRepository


class AuditTrailService:
    """Store and query actor/action/resource audit events.

    The optional fallback is for API availability during dependency outages and
    tests; production events are persisted through the injected request-scoped
    SQLAlchemy session.
    """

    def __init__(self) -> None:
        self._fallback: list[dict[str, Any]] = []
        self._repository = AuditRepository()

    def record(
        self,
        *,
        actor: str,
        action: str,
        resource_type: str,
        actor_type: str = "user",
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        status: str = "success",
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session: Session | None = None,
    ) -> dict[str, Any]:
        payload = details or {}
        if session is not None:
            entry = AuditEntry(
                actor=actor,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=payload,
                event_metadata=metadata or payload,
                actor_type=actor_type,
                status=status,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            return self._serialize(self._repository.create(session, entry))

        record = {
            "id": str(uuid.uuid4()),
            "actor": actor,
            "actor_id": actor,
            "actor_type": actor_type,
            "event_id": str(uuid.uuid4()),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": payload,
            "metadata": metadata or payload,
            "status": status,
            "request_id": request_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._fallback.append(record)
        return record

    def query(
        self,
        *,
        session: Session | None = None,
        actor: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
        resource_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, 500))
        if session is not None:
            entries = self._repository.query(session, actor_id=actor, action=action, resource_type=resource_type,
                resource_id=resource_id, status=status, search=search, start_at=start_at, end_at=end_at,
                offset=offset, limit=bounded_limit)
            return [self._serialize(entry) for entry in entries]

        records = list(reversed(self._fallback))
        if actor:
            records = [item for item in records if item["actor"] == actor]
        if action:
            records = [item for item in records if item["action"] == action]
        if resource_type:
            records = [item for item in records if item["resource_type"] == resource_type]
        if resource_id:
            records = [item for item in records if item["resource_id"] == resource_id]
        if status:
            records = [item for item in records if item["status"] == status]
        if search:
            needle = search.lower()
            records = [item for item in records if needle in item["actor"].lower() or needle in item["action"].lower() or needle in item["resource_type"].lower()]
        return records[max(offset, 0):max(offset, 0) + bounded_limit]

    def get(self, audit_id: str, session: Session | None = None) -> dict[str, Any] | None:
        if session is not None:
            entry = self._repository.get(session, audit_id)
            return self._serialize(entry) if entry else None
        return next((item for item in self._fallback if item["id"] == audit_id), None)

    def export(self, *, session: Session | None = None, format: str = "json", **filters: Any) -> list[dict[str, Any]]:
        if format not in {"json", "csv"}:
            raise ValueError("format must be json or csv")
        return self.query(session=session, limit=500, **filters)

    @staticmethod
    def _serialize(entry: AuditEntry) -> dict[str, Any]:
        return {
            "id": str(entry.id),
            "actor": entry.actor,
            "actor_id": entry.actor,
            "actor_type": entry.actor_type,
            "event_id": entry.event_id,
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "details": entry.details,
            "metadata": entry.event_metadata,
            "status": entry.status,
            "request_id": entry.request_id,
            "ip_address": entry.ip_address,
            "user_agent": entry.user_agent,
            "occurred_at": entry.occurred_at.isoformat(),
            "created_at": entry.created_at.isoformat(),
        }


audit_trail_service = AuditTrailService()
