"""Phase 12.3.4 — Activity Feed Service.

Logs and retrieves collaborative activity streams across datasets, analyses,
dashboards, reports, forecasts, and comments.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from backend.app.models.collaboration import Activity
from backend.app.repositories.collaboration_repository import ActivityRepository

logger = logging.getLogger(__name__)


class ActivityService:
    """Service capturing and serving workspace activity streams."""

    def __init__(self, repository: Optional[ActivityRepository] = None) -> None:
        self.repo = repository or ActivityRepository()

    def record_activity(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        actor_id: uuid.UUID | str,
        actor_name: str,
        action: str,
        resource_type: str,
        resource_id: str,
        summary: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> Activity:
        """Record an activity event."""
        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        aid = uuid.UUID(str(actor_id)) if isinstance(actor_id, str) else actor_id

        if not summary:
            summary = f"{actor_name} performed {action} on {resource_type}:{resource_id}"

        activity = Activity(
            tenant_id=tid,
            workspace_id=wid,
            actor_id=aid,
            actor_name=actor_name,
            action=action.upper(),
            resource_type=resource_type.lower(),
            resource_id=str(resource_id),
            summary=summary,
            details=details or {},
            timestamp=datetime.now(timezone.utc),
        )

        saved = self.repo.record_activity(activity)
        logger.info(
            "Activity logged: [%s] %s by %s on %s:%s (ws=%s)",
            activity.action,
            summary,
            actor_name,
            resource_type,
            resource_id,
            wid,
        )
        return saved

    def get_feed(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        actor_id: Optional[uuid.UUID | str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Activity]:
        """Fetch filtered activity feed for a workspace."""
        return self.repo.list_activities(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            action=action.upper() if action else None,
            resource_type=resource_type.lower() if resource_type else None,
            resource_id=str(resource_id) if resource_id else None,
            limit=limit,
        )
