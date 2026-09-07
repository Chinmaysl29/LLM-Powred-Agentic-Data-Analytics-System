"""Phase 12.3.3 — Mention System Service.

Extracts, validates, and notifies users when mentioned via @username in comments.
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Dict, List, Optional, Set
import uuid

from backend.app.models.collaboration import Comment, Mention, NotificationType
from backend.app.repositories.collaboration_repository import MentionRepository
from backend.app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

MENTION_REGEX = re.compile(r"@([a-zA-Z0-9_\.-]+)")


class MentionService:
    """Service handling @username parsing, validation, and mention alerts."""

    def __init__(
        self,
        repository: Optional[MentionRepository] = None,
        notification_service: Optional[NotificationService] = None,
        user_resolver: Optional[Callable[[str], Optional[uuid.UUID]]] = None,
    ) -> None:
        self.repo = repository or MentionRepository()
        self.notification_service = notification_service or NotificationService()
        # Optional custom resolver: username -> UUID
        self._user_resolver = user_resolver
        # Fallback dictionary for testing / mock user registry
        self._user_lookup: Dict[str, uuid.UUID] = {}

    def register_user_alias(self, username: str, user_id: uuid.UUID | str) -> None:
        """Register a known username -> user_id mapping for validation."""
        clean_user = username.lstrip("@").lower()
        self._user_lookup[clean_user] = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id

    def extract_mentions(self, text: str) -> List[str]:
        """Extract all unique @usernames mentioned in text."""
        if not text:
            return []
        matches = MENTION_REGEX.findall(text)
        # Deduplicate while preserving order
        seen: Set[str] = set()
        result = []
        for m in matches:
            clean = m.lower()
            if clean not in seen:
                seen.add(clean)
                result.append(clean)
        return result

    def resolve_user(self, username: str) -> Optional[uuid.UUID]:
        """Resolve a username to a UUID, using resolver or lookup cache."""
        clean = username.lstrip("@").lower()
        if self._user_resolver:
            resolved = self._user_resolver(clean)
            if resolved:
                return resolved
        return self._user_lookup.get(clean)

    def process_mentions(
        self,
        comment: Comment,
        author_id: uuid.UUID | str,
        author_name: str,
    ) -> List[Mention]:
        """Parse mentions from a comment, validate them, save records and notify users."""
        usernames = self.extract_mentions(comment.content)
        created_mentions: List[Mention] = []

        for uname in usernames:
            target_user_id = self.resolve_user(uname)
            if not target_user_id:
                logger.warning("Mentioned user @%s could not be resolved or does not exist", uname)
                continue

            # Don't notify the author if they mention themselves
            if str(target_user_id) == str(author_id):
                continue

            mention = Mention(
                tenant_id=comment.tenant_id,
                workspace_id=comment.workspace_id,
                comment_id=comment.id,
                mentioned_user_id=target_user_id,
                mentioner_user_id=uuid.UUID(str(author_id)) if isinstance(author_id, str) else author_id,
                username=uname,
                is_read=False,
            )
            saved = self.repo.create_mention(mention)
            created_mentions.append(saved)

            # Trigger notification
            self.notification_service.send_notification(
                tenant_id=comment.tenant_id,
                workspace_id=comment.workspace_id,
                user_id=target_user_id,
                notification_type=NotificationType.MENTION,
                title=f"Mentioned by {author_name}",
                message=f"{author_name} mentioned you in a comment on {comment.resource_type}:{comment.resource_id}: \"{comment.content[:100]}\"",
                payload={
                    "comment_id": str(comment.id),
                    "resource_type": comment.resource_type,
                    "resource_id": comment.resource_id,
                    "mention_id": str(saved.id),
                },
            )

        return created_mentions

    def get_user_mentions(
        self,
        user_id: uuid.UUID | str,
        is_read: Optional[bool] = None,
    ) -> List[Mention]:
        """Fetch mentions targeting the specified user."""
        return self.repo.list_mentions(user_id=user_id, is_read=is_read)

    def mark_mention_read(self, mention_id: uuid.UUID | str) -> bool:
        """Mark a mention as read."""
        return self.repo.mark_as_read(mention_id)
