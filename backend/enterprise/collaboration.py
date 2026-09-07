"""Phase 12.3 — Team Collaboration System

Provides threaded commenting, user mentions, shared query templates,
activity streaming, and team bookmarks across datasets, dashboards, and reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class Comment:
    id: str
    tenant_id: str
    workspace_id: str
    target_type: str  # "dataset", "dashboard", "report", "forecast"
    target_id: str
    author_id: str
    author_name: str
    content: str
    thread_id: Optional[str] = None
    mentions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "content": self.content,
            "thread_id": self.thread_id,
            "mentions": self.mentions,
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class SharedTemplate:
    id: str
    tenant_id: str
    workspace_id: str
    title: str
    sql_or_prompt: str
    author_id: str
    author_name: str
    tags: List[str] = field(default_factory=list)
    description: str = ""
    usage_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "title": self.title,
            "sql_or_prompt": self.sql_or_prompt,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "tags": self.tags,
            "description": self.description,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ActivityEvent:
    id: str
    tenant_id: str
    workspace_id: str
    user_id: str
    user_name: str
    action: str  # "CREATED", "UPDATED", "SHARED", "COMMENTED", "RESOLVED"
    target_type: str
    target_id: str
    summary: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TeamBookmark:
    id: str
    tenant_id: str
    workspace_id: str
    user_id: str
    name: str
    state_payload: Dict[str, Any]
    is_shared: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "name": self.name,
            "state_payload": self.state_payload,
            "is_shared": self.is_shared,
            "created_at": self.created_at.isoformat(),
        }


class CollaborationManager:
    """Singleton coordinator for team comments, templates, bookmarks, and activity feeds."""

    _instance: Optional[CollaborationManager] = None

    def __new__(cls) -> CollaborationManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._comments: Dict[str, Comment] = {}
            cls._instance._templates: Dict[str, SharedTemplate] = {}
            cls._instance._activities: List[ActivityEvent] = []
            cls._instance._bookmarks: Dict[str, TeamBookmark] = {}
        return cls._instance

    @staticmethod
    def extract_mentions(text: str) -> List[str]:
        """Extract @mentions from text content."""
        return list(set(re.findall(r"@([a-zA-Z0-9_\.\-]+)", text)))

    def add_comment(
        self,
        tenant_id: str,
        workspace_id: str,
        target_type: str,
        target_id: str,
        author_id: str,
        author_name: str,
        content: str,
        thread_id: Optional[str] = None,
    ) -> Comment:
        """Add comment or reply in a discussion thread."""
        comment_id = f"cmt-{uuid.uuid4().hex[:12]}"
        mentions = self.extract_mentions(content)

        comment = Comment(
            id=comment_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            target_type=target_type,
            target_id=target_id,
            author_id=author_id,
            author_name=author_name,
            content=content,
            thread_id=thread_id or comment_id,
            mentions=mentions,
        )
        self._comments[comment_id] = comment

        self.record_activity(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            user_id=author_id,
            user_name=author_name,
            action="COMMENTED",
            target_type=target_type,
            target_id=target_id,
            summary=f"{author_name} commented on {target_type} '{target_id}'",
        )
        return comment

    def resolve_thread(self, thread_id: str, resolved_by_id: str) -> int:
        """Mark all comments in a thread as resolved."""
        count = 0
        now = datetime.now(timezone.utc)
        for comment in self._comments.values():
            if comment.thread_id == thread_id:
                comment.resolved = True
                comment.resolved_by = resolved_by_id
                comment.resolved_at = now
                count += 1
        return count

    def list_comments(
        self,
        target_type: str,
        target_id: str,
        include_resolved: bool = True,
    ) -> List[Comment]:
        """Retrieve comments for a specific entity."""
        items = [
            c
            for c in self._comments.values()
            if c.target_type == target_type and c.target_id == target_id
        ]
        if not include_resolved:
            items = [c for c in items if not c.resolved]
        return sorted(items, key=lambda x: x.created_at)

    def create_template(
        self,
        tenant_id: str,
        workspace_id: str,
        title: str,
        sql_or_prompt: str,
        author_id: str,
        author_name: str,
        tags: Optional[List[str]] = None,
        description: str = "",
    ) -> SharedTemplate:
        """Publish a shared SQL or prompt query template."""
        tmpl_id = f"tmpl-{uuid.uuid4().hex[:12]}"
        tmpl = SharedTemplate(
            id=tmpl_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            title=title,
            sql_or_prompt=sql_or_prompt,
            author_id=author_id,
            author_name=author_name,
            tags=tags or [],
            description=description,
        )
        self._templates[tmpl_id] = tmpl
        return tmpl

    def list_templates(
        self,
        tenant_id: str,
        workspace_id: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[SharedTemplate]:
        """Search query templates by workspace or tag."""
        res = [t for t in self._templates.values() if t.tenant_id == tenant_id]
        if workspace_id:
            res = [t for t in res if t.workspace_id == workspace_id]
        if tag:
            res = [t for t in res if tag.lower() in [x.lower() for x in t.tags]]
        return res

    def use_template(self, template_id: str) -> SharedTemplate:
        """Increment usage count for a template."""
        tmpl = self._templates.get(template_id)
        if not tmpl:
            raise KeyError(f"Template {template_id} not found")
        tmpl.usage_count += 1
        return tmpl

    def record_activity(
        self,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
        user_name: str,
        action: str,
        target_type: str,
        target_id: str,
        summary: str,
    ) -> ActivityEvent:
        """Append an event to the team activity stream."""
        event = ActivityEvent(
            id=f"act-{uuid.uuid4().hex[:12]}",
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            user_id=user_id,
            user_name=user_name,
            action=action,
            target_type=target_type,
            target_id=target_id,
            summary=summary,
        )
        self._activities.append(event)
        return event

    def get_activity_feed(
        self,
        tenant_id: str,
        workspace_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ActivityEvent]:
        """Retrieve recent team activity events in reverse chronological order."""
        res = [a for a in self._activities if a.tenant_id == tenant_id]
        if workspace_id:
            res = [a for a in res if a.workspace_id == workspace_id]
        return sorted(res, key=lambda x: x.timestamp, reverse=True)[:limit]

    def save_bookmark(
        self,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
        name: str,
        state_payload: Dict[str, Any],
        is_shared: bool = False,
    ) -> TeamBookmark:
        """Save a filter / chart state bookmark."""
        bm_id = f"bm-{uuid.uuid4().hex[:12]}"
        bm = TeamBookmark(
            id=bm_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            user_id=user_id,
            name=name,
            state_payload=state_payload,
            is_shared=is_shared,
        )
        self._bookmarks[bm_id] = bm
        return bm

    def list_bookmarks(
        self,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
    ) -> List[TeamBookmark]:
        """List personal and shared bookmarks for a workspace."""
        return [
            b
            for b in self._bookmarks.values()
            if b.tenant_id == tenant_id
            and b.workspace_id == workspace_id
            and (b.user_id == user_id or b.is_shared)
        ]

    def reset(self) -> None:
        """Reset storage for testing."""
        self._comments.clear()
        self._templates.clear()
        self._activities.clear()
        self._bookmarks.clear()
