"""Phase 12.3.2 — Comment System Service.

Handles CRUD operations, replies/threading, resolution, mention extraction,
and activity logging for comments across reports, dashboards, datasets, and forecasts.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import List, Optional
import uuid

from backend.app.models.collaboration import Comment
from backend.app.repositories.collaboration_repository import CommentRepository
from backend.app.services.activity_service import ActivityService
from backend.app.services.mention_service import MentionService

logger = logging.getLogger(__name__)

ALLOWED_RESOURCE_TYPES = {"report", "dashboard", "dataset", "forecast", "task"}


class CommentService:
    """Service managing comments on analytics resources."""

    def __init__(
        self,
        repository: Optional[CommentRepository] = None,
        mention_service: Optional[MentionService] = None,
        activity_service: Optional[ActivityService] = None,
    ) -> None:
        self.repo = repository or CommentRepository()
        self.mention_service = mention_service or MentionService()
        self.activity_service = activity_service or ActivityService()

    def add_comment(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        author_id: uuid.UUID | str,
        author_name: str,
        resource_type: str,
        resource_id: str,
        content: str,
        parent_id: Optional[uuid.UUID | str] = None,
        project_id: Optional[uuid.UUID | str] = None,
    ) -> Comment:
        """Add a comment or reply to an analytics resource."""
        res_type = resource_type.strip().lower()
        if res_type not in ALLOWED_RESOURCE_TYPES:
            raise ValueError(f"Invalid resource_type '{resource_type}'. Allowed: {sorted(ALLOWED_RESOURCE_TYPES)}")

        clean_content = content.strip()
        if not clean_content:
            raise ValueError("Comment content cannot be empty.")

        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        aid = uuid.UUID(str(author_id)) if isinstance(author_id, str) else author_id
        pid = uuid.UUID(str(parent_id)) if parent_id else None
        proj_id = uuid.UUID(str(project_id)) if project_id else None

        comment = Comment(
            tenant_id=tid,
            workspace_id=wid,
            project_id=proj_id,
            author_id=aid,
            author_name=author_name,
            resource_type=res_type,
            resource_id=str(resource_id),
            content=clean_content,
            parent_id=pid,
            is_edited=False,
            is_resolved=False,
        )

        saved = self.repo.create_comment(comment)

        # Process mentions
        self.mention_service.process_mentions(saved, author_id=aid, author_name=author_name)

        # Log activity
        action = "REPLY_ADDED" if pid else "COMMENT_ADDED"
        self.activity_service.record_activity(
            tenant_id=tid,
            workspace_id=wid,
            actor_id=aid,
            actor_name=author_name,
            action=action,
            resource_type=res_type,
            resource_id=str(resource_id),
            summary=f"{author_name} commented on {res_type}:{resource_id}",
            details={"comment_id": str(saved.id), "parent_id": str(pid) if pid else None},
        )

        logger.info("Comment created id=%s on %s:%s by %s", saved.id, res_type, resource_id, author_name)
        return saved

    def edit_comment(
        self,
        comment_id: uuid.UUID | str,
        new_content: str,
        author_id: uuid.UUID | str,
    ) -> Comment:
        """Edit an existing comment's text."""
        comment = self.repo.get_comment(comment_id)
        if not comment:
            raise ValueError(f"Comment with id '{comment_id}' not found.")

        aid = uuid.UUID(str(author_id)) if isinstance(author_id, str) else author_id
        if comment.author_id != aid:
            raise PermissionError("Only the original author can edit this comment.")

        clean_content = new_content.strip()
        if not clean_content:
            raise ValueError("Updated content cannot be empty.")

        comment.content = clean_content
        comment.is_edited = True
        saved = self.repo.update_comment(comment)

        # Reprocess any newly added mentions
        self.mention_service.process_mentions(saved, author_id=aid, author_name=comment.author_name)

        logger.info("Comment id=%s edited by author %s", comment_id, author_id)
        return saved

    def delete_comment(
        self,
        comment_id: uuid.UUID | str,
        user_id: uuid.UUID | str,
        is_admin: bool = False,
    ) -> bool:
        """Delete a comment."""
        comment = self.repo.get_comment(comment_id)
        if not comment:
            return False

        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        if comment.author_id != uid and not is_admin:
            raise PermissionError("You do not have permission to delete this comment.")

        deleted = self.repo.delete_comment(comment_id)
        if deleted:
            logger.info("Comment id=%s deleted by user %s", comment_id, user_id)
        return deleted

    def list_comments(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        parent_id: Optional[uuid.UUID | str] = None,
    ) -> List[Comment]:
        """List comments for a specific resource, workspace, or thread."""
        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        pid = uuid.UUID(str(parent_id)) if parent_id else None
        return self.repo.list_comments(
            tenant_id=tid,
            workspace_id=wid,
            resource_type=resource_type.lower() if resource_type else None,
            resource_id=str(resource_id) if resource_id else None,
            parent_id=pid,
        )

    def resolve_comment(
        self,
        comment_id: uuid.UUID | str,
        resolved_by: uuid.UUID | str,
    ) -> Comment:
        """Mark a comment thread as resolved."""
        comment = self.repo.get_comment(comment_id)
        if not comment:
            raise ValueError(f"Comment with id '{comment_id}' not found.")

        rid = uuid.UUID(str(resolved_by)) if isinstance(resolved_by, str) else resolved_by
        comment.is_resolved = True
        comment.resolved_by = rid
        comment.resolved_at = datetime.now(timezone.utc)
        saved = self.repo.update_comment(comment)

        logger.info("Comment id=%s marked as resolved by %s", comment_id, resolved_by)
        return saved
