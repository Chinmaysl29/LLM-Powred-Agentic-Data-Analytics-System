"""Phase 12.3 — Collaboration Repositories.

Database repositories for Comment, Mention, Activity, Task, and Notification models,
supporting both SQLAlchemy sessions and an in-memory test fallback.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.models.collaboration import (
    Activity,
    Comment,
    Mention,
    Notification,
    Task,
    TaskPriority,
    TaskStatus,
)

logger = logging.getLogger(__name__)


def _ensure_timestamps(entity: object) -> None:
    now = datetime.now(timezone.utc)
    if not getattr(entity, "created_at", None):
        entity.created_at = now
    if not getattr(entity, "updated_at", None):
        entity.updated_at = now


# ---------------------------------------------------------------------------
# Comment Repository
# ---------------------------------------------------------------------------
class CommentRepository:
    """Repository for Comment persistence and querying."""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db
        self._memory_store: dict[uuid.UUID, Comment] = {}

    def create_comment(self, comment: Comment) -> Comment:
        if not comment.id:
            comment.id = uuid.uuid4()
        _ensure_timestamps(comment)
        if self.db is not None:
            self.db.add(comment)
            self.db.commit()
            self.db.refresh(comment)
        else:
            self._memory_store[comment.id] = comment
        return comment

    def get_comment(self, comment_id: uuid.UUID | str) -> Optional[Comment]:
        cid = uuid.UUID(str(comment_id)) if isinstance(comment_id, str) else comment_id
        if self.db is not None:
            return self.db.get(Comment, cid)
        return self._memory_store.get(cid)

    def list_comments(
        self,
        tenant_id: uuid.UUID,
        workspace_id: uuid.UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        parent_id: Optional[uuid.UUID] = None,
    ) -> List[Comment]:
        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        pid = uuid.UUID(str(parent_id)) if isinstance(parent_id, str) else parent_id

        if self.db is not None:
            query = select(Comment).where(
                Comment.tenant_id == tid,
                Comment.workspace_id == wid,
            )
            if resource_type:
                query = query.where(Comment.resource_type == resource_type)
            if resource_id:
                query = query.where(Comment.resource_id == resource_id)
            if pid is not None:
                query = query.where(Comment.parent_id == pid)
            query = query.order_by(Comment.created_at.asc())
            return list(self.db.scalars(query).all())

        results = [
            c for c in self._memory_store.values()
            if c.tenant_id == tid and c.workspace_id == wid
        ]
        if resource_type:
            results = [c for c in results if c.resource_type == resource_type]
        if resource_id:
            results = [c for c in results if c.resource_id == resource_id]
        if pid is not None:
            results = [c for c in results if c.parent_id == pid]
        results.sort(key=lambda x: x.created_at)
        return results

    def update_comment(self, comment: Comment) -> Comment:
        comment.updated_at = datetime.now(timezone.utc)
        if self.db is not None:
            self.db.add(comment)
            self.db.commit()
            self.db.refresh(comment)
        else:
            self._memory_store[comment.id] = comment
        return comment

    def delete_comment(self, comment_id: uuid.UUID | str) -> bool:
        cid = uuid.UUID(str(comment_id)) if isinstance(comment_id, str) else comment_id
        if self.db is not None:
            comment = self.get_comment(cid)
            if comment:
                self.db.delete(comment)
                self.db.commit()
                return True
            return False
        return self._memory_store.pop(cid, None) is not None


# ---------------------------------------------------------------------------
# Mention Repository
# ---------------------------------------------------------------------------
class MentionRepository:
    """Repository for Mention records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db
        self._memory_store: dict[uuid.UUID, Mention] = {}

    def create_mention(self, mention: Mention) -> Mention:
        if not mention.id:
            mention.id = uuid.uuid4()
        _ensure_timestamps(mention)
        if self.db is not None:
            self.db.add(mention)
            self.db.commit()
            self.db.refresh(mention)
        else:
            self._memory_store[mention.id] = mention
        return mention

    def list_mentions(
        self,
        user_id: uuid.UUID | str,
        is_read: Optional[bool] = None,
    ) -> List[Mention]:
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        if self.db is not None:
            query = select(Mention).where(Mention.mentioned_user_id == uid)
            if is_read is not None:
                query = query.where(Mention.is_read == is_read)
            query = query.order_by(Mention.created_at.desc())
            return list(self.db.scalars(query).all())

        results = [m for m in self._memory_store.values() if m.mentioned_user_id == uid]
        if is_read is not None:
            results = [m for m in results if m.is_read == is_read]
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    def mark_as_read(self, mention_id: uuid.UUID | str) -> bool:
        mid = uuid.UUID(str(mention_id)) if isinstance(mention_id, str) else mention_id
        if self.db is not None:
            mention = self.db.get(Mention, mid)
            if mention:
                mention.is_read = True
                self.db.commit()
                return True
            return False
        if mid in self._memory_store:
            self._memory_store[mid].is_read = True
            return True
        return False


# ---------------------------------------------------------------------------
# Activity Repository
# ---------------------------------------------------------------------------
class ActivityRepository:
    """Repository for storing and querying the Activity audit trail."""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db
        self._memory_store: dict[uuid.UUID, Activity] = {}

    def record_activity(self, activity: Activity) -> Activity:
        if not activity.id:
            activity.id = uuid.uuid4()
        _ensure_timestamps(activity)
        if not getattr(activity, "timestamp", None):
            activity.timestamp = datetime.now(timezone.utc)
        if self.db is not None:
            self.db.add(activity)
            self.db.commit()
            self.db.refresh(activity)
        else:
            self._memory_store[activity.id] = activity
        return activity

    def list_activities(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        actor_id: Optional[uuid.UUID | str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Activity]:
        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        aid = uuid.UUID(str(actor_id)) if actor_id else None

        if self.db is not None:
            query = select(Activity).where(
                Activity.tenant_id == tid,
                Activity.workspace_id == wid,
            )
            if aid is not None:
                query = query.where(Activity.actor_id == aid)
            if action:
                query = query.where(Activity.action == action)
            if resource_type:
                query = query.where(Activity.resource_type == resource_type)
            if resource_id:
                query = query.where(Activity.resource_id == resource_id)
            query = query.order_by(desc(Activity.timestamp)).limit(limit)
            return list(self.db.scalars(query).all())

        results = [
            a for a in self._memory_store.values()
            if a.tenant_id == tid and a.workspace_id == wid
        ]
        if aid is not None:
            results = [a for a in results if a.actor_id == aid]
        if action:
            results = [a for a in results if a.action == action]
        if resource_type:
            results = [a for a in results if a.resource_type == resource_type]
        if resource_id:
            results = [a for a in results if a.resource_id == resource_id]
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results[:limit]


# ---------------------------------------------------------------------------
# Task Repository
# ---------------------------------------------------------------------------
class TaskRepository:
    """Repository for Task entities."""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db
        self._memory_store: dict[uuid.UUID, Task] = {}

    def create_task(self, task: Task) -> Task:
        if not task.id:
            task.id = uuid.uuid4()
        _ensure_timestamps(task)
        if self.db is not None:
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
        else:
            self._memory_store[task.id] = task
        return task

    def get_task(self, task_id: uuid.UUID | str) -> Optional[Task]:
        tid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
        if self.db is not None:
            return self.db.get(Task, tid)
        return self._memory_store.get(tid)

    def list_tasks(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        project_id: Optional[uuid.UUID | str] = None,
        assigned_to: Optional[uuid.UUID | str] = None,
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        pid = uuid.UUID(str(project_id)) if project_id else None
        asgn = uuid.UUID(str(assigned_to)) if assigned_to else None

        if self.db is not None:
            query = select(Task).where(
                Task.tenant_id == tid,
                Task.workspace_id == wid,
            )
            if pid is not None:
                query = query.where(Task.project_id == pid)
            if asgn is not None:
                query = query.where(Task.assigned_to == asgn)
            if status is not None:
                query = query.where(Task.status == status)
            query = query.order_by(Task.created_at.desc())
            return list(self.db.scalars(query).all())

        results = [
            t for t in self._memory_store.values()
            if t.tenant_id == tid and t.workspace_id == wid
        ]
        if pid is not None:
            results = [t for t in results if t.project_id == pid]
        if asgn is not None:
            results = [t for t in results if t.assigned_to == asgn]
        if status is not None:
            results = [t for t in results if t.status == status]
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results

    def update_task(self, task: Task) -> Task:
        task.updated_at = datetime.now(timezone.utc)
        if self.db is not None:
            self.db.add(task)
            self.db.commit()
            self.db.refresh(task)
        else:
            self._memory_store[task.id] = task
        return task

    def delete_task(self, task_id: uuid.UUID | str) -> bool:
        tid = uuid.UUID(str(task_id)) if isinstance(task_id, str) else task_id
        if self.db is not None:
            task = self.get_task(tid)
            if task:
                self.db.delete(task)
                self.db.commit()
                return True
            return False
        return self._memory_store.pop(tid, None) is not None


# ---------------------------------------------------------------------------
# Notification Repository
# ---------------------------------------------------------------------------
class NotificationRepository:
    """Repository for in-app and delivered Notification records."""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db
        self._memory_store: dict[uuid.UUID, Notification] = {}

    def create_notification(self, notification: Notification) -> Notification:
        if not notification.id:
            notification.id = uuid.uuid4()
        _ensure_timestamps(notification)
        if self.db is not None:
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
        else:
            self._memory_store[notification.id] = notification
        return notification

    def get_notification(self, notification_id: uuid.UUID | str) -> Optional[Notification]:
        nid = uuid.UUID(str(notification_id)) if isinstance(notification_id, str) else notification_id
        if self.db is not None:
            return self.db.get(Notification, nid)
        return self._memory_store.get(nid)

    def list_notifications(
        self,
        user_id: uuid.UUID | str,
        is_read: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Notification]:
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        if self.db is not None:
            query = select(Notification).where(Notification.user_id == uid)
            if is_read is not None:
                query = query.where(Notification.is_read == is_read)
            query = query.order_by(desc(Notification.created_at)).limit(limit)
            return list(self.db.scalars(query).all())

        results = [n for n in self._memory_store.values() if n.user_id == uid]
        if is_read is not None:
            results = [n for n in results if n.is_read == is_read]
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]

    def mark_as_read(self, notification_id: uuid.UUID | str) -> bool:
        nid = uuid.UUID(str(notification_id)) if isinstance(notification_id, str) else notification_id
        now = datetime.now(timezone.utc)
        if self.db is not None:
            notification = self.db.get(Notification, nid)
            if notification:
                notification.is_read = True
                notification.read_at = now
                self.db.commit()
                return True
            return False
        if nid in self._memory_store:
            self._memory_store[nid].is_read = True
            self._memory_store[nid].read_at = now
            return True
        return False

    def mark_all_read(self, user_id: uuid.UUID | str) -> int:
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        now = datetime.now(timezone.utc)
        count = 0
        if self.db is not None:
            query = select(Notification).where(
                Notification.user_id == uid,
                Notification.is_read == False,
            )
            unread = self.db.scalars(query).all()
            for n in unread:
                n.is_read = True
                n.read_at = now
                count += 1
            self.db.commit()
            return count

        for n in self._memory_store.values():
            if n.user_id == uid and not n.is_read:
                n.is_read = True
                n.read_at = now
                count += 1
        return count

    def get_unread_count(self, user_id: uuid.UUID | str) -> int:
        uid = uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        if self.db is not None:
            from sqlalchemy import func
            query = select(func.count(Notification.id)).where(
                Notification.user_id == uid,
                Notification.is_read == False,
            )
            return self.db.scalar(query) or 0

        return sum(1 for n in self._memory_store.values() if n.user_id == uid and not n.is_read)
