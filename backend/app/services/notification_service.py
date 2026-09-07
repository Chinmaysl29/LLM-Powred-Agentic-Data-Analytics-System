"""Phase 12.3.8 — Notification Engine.

Dispatches in-app notifications and email-ready delivery across mentions,
comments, task assignments, and completed pipelines.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from backend.app.models.collaboration import (
    Notification,
    NotificationChannel,
    NotificationType,
)
from backend.app.repositories.collaboration_repository import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Service orchestrating user notifications across channels."""

    def __init__(self, repository: Optional[NotificationRepository] = None) -> None:
        self.repo = repository or NotificationRepository()

    def send_notification(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        user_id: uuid.UUID | str,
        notification_type: NotificationType | str,
        title: str,
        message: str,
        channel: NotificationChannel | str = NotificationChannel.IN_APP,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """Create and dispatch a notification to the target user."""
        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        
        ntype = (
            NotificationType(notification_type)
            if isinstance(notification_type, str)
            else notification_type
        )
        nchan = (
            NotificationChannel(channel)
            if isinstance(channel, str)
            else channel
        )

        notification = Notification(
            tenant_id=tid,
            workspace_id=wid,
            user_id=uid,
            type=ntype,
            title=title,
            message=message,
            channel=nchan,
            payload=payload or {},
            is_read=False,
        )
        saved = self.repo.create_notification(notification)

        if nchan == NotificationChannel.EMAIL:
            # Future-ready email gateway stub
            logger.info(
                "Email notification queued for user %s: %s - %s",
                uid,
                title,
                message,
            )
        else:
            logger.info(
                "In-App notification sent to user %s: %s (%s)",
                uid,
                title,
                ntype.value,
            )

        return saved

    def get_user_notifications(
        self,
        user_id: uuid.UUID | str,
        is_read: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Notification]:
        """Fetch notification inbox for a user."""
        return self.repo.list_notifications(user_id, is_read=is_read, limit=limit)

    def mark_notification_read(self, notification_id: uuid.UUID | str) -> bool:
        """Mark a single notification as read."""
        return self.repo.mark_as_read(notification_id)

    def mark_all_notifications_read(self, user_id: uuid.UUID | str) -> int:
        """Mark all unread notifications as read for a given user."""
        return self.repo.mark_all_read(user_id)

    def get_unread_count(self, user_id: uuid.UUID | str) -> int:
        """Get the count of unread notifications."""
        return self.repo.get_unread_count(user_id)
