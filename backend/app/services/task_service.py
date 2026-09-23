"""Phase 12.3.5 — Task Assignment Service.

Manages task creation, assignment, status lifecycles, priority levels,
due dates, and assignment notifications.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import List, Optional
import uuid

from backend.app.models.collaboration import (
    NotificationType,
    Task,
    TaskPriority,
    TaskStatus,
)
from backend.app.repositories.collaboration_repository import TaskRepository
from backend.app.services.activity_service import ActivityService
from backend.app.services.comment_service import CommentService
from backend.app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class TaskService:
    """Service managing collaborative tasks."""

    def __init__(
        self,
        repository: Optional[TaskRepository] = None,
        notification_service: Optional[NotificationService] = None,
        activity_service: Optional[ActivityService] = None,
        comment_service: Optional[CommentService] = None,
    ) -> None:
        self.repo = repository or TaskRepository()
        self.notification_service = notification_service or NotificationService()
        self.activity_service = activity_service or ActivityService()
        self.comment_service = comment_service or CommentService()

    def create_task(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        created_by: uuid.UUID | str,
        title: str,
        description: str = "",
        project_id: Optional[uuid.UUID | str] = None,
        priority: TaskPriority | str = TaskPriority.MEDIUM,
        due_date: Optional[datetime] = None,
        assigned_to: Optional[uuid.UUID | str] = None,
    ) -> Task:
        """Create a collaborative task."""
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title cannot be empty.")

        tid = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        wid = uuid.UUID(str(workspace_id)) if isinstance(workspace_id, str) else workspace_id
        cb = uuid.UUID(str(created_by)) if isinstance(created_by, str) else created_by
        pid = uuid.UUID(str(project_id)) if project_id else None
        asgn = uuid.UUID(str(assigned_to)) if assigned_to else None
        tpri = TaskPriority(priority) if isinstance(priority, str) else priority

        task = Task(
            tenant_id=tid,
            workspace_id=wid,
            project_id=pid,
            title=clean_title,
            description=description.strip(),
            status=TaskStatus.TODO,
            priority=tpri,
            due_date=due_date,
            assigned_to=asgn,
            created_by=cb,
        )

        saved = self.repo.create_task(task)

        # Notify assignee if assigned at creation
        if asgn and asgn != cb:
            self.notification_service.send_notification(
                tenant_id=tid,
                workspace_id=wid,
                user_id=asgn,
                notification_type=NotificationType.TASK_ASSIGNED,
                title="New Task Assigned",
                message=f"You have been assigned to task: '{clean_title}'",
                payload={"task_id": str(saved.id)},
            )

        self.activity_service.record_activity(
            tenant_id=tid,
            workspace_id=wid,
            actor_id=cb,
            actor_name="System/User",
            action="TASK_CREATED",
            resource_type="task",
            resource_id=str(saved.id),
            summary=f"Task '{clean_title}' created",
            details={"priority": tpri.value, "assigned_to": str(asgn) if asgn else None},
        )

        logger.info("Task id=%s '%s' created in ws=%s", saved.id, clean_title, wid)
        return saved

    def assign_task(
        self,
        task_id: uuid.UUID | str,
        assigned_to: uuid.UUID | str,
        assigned_by: uuid.UUID | str,
    ) -> Task:
        """Assign or reassign a task to a user."""
        task = self.repo.get_task(task_id)
        if not task:
            raise ValueError(f"Task with id '{task_id}' not found.")

        target_uid = uuid.UUID(str(assigned_to)) if isinstance(assigned_to, str) else assigned_to
        by_uid = uuid.UUID(str(assigned_by)) if isinstance(assigned_by, str) else assigned_by

        task.assigned_to = target_uid
        saved = self.repo.update_task(task)

        self.notification_service.send_notification(
            tenant_id=task.tenant_id,
            workspace_id=task.workspace_id,
            user_id=target_uid,
            notification_type=NotificationType.TASK_ASSIGNED,
            title="Task Assigned",
            message=f"You have been assigned to task: '{task.title}'",
            payload={"task_id": str(task.id)},
        )

        logger.info("Task id=%s reassigned to %s", task.id, target_uid)
        return saved

    def update_status(
        self,
        task_id: uuid.UUID | str,
        status: TaskStatus | str,
        updated_by: uuid.UUID | str,
    ) -> Task:
        """Update the status of a task."""
        task = self.repo.get_task(task_id)
        if not task:
            raise ValueError(f"Task with id '{task_id}' not found.")

        tstat = TaskStatus(status) if isinstance(status, str) else status
        old_stat = task.status
        task.status = tstat
        saved = self.repo.update_task(task)

        by_uid = uuid.UUID(str(updated_by)) if isinstance(updated_by, str) else updated_by
        self.activity_service.record_activity(
            tenant_id=task.tenant_id,
            workspace_id=task.workspace_id,
            actor_id=by_uid,
            actor_name="Task User",
            action="TASK_STATUS_UPDATED",
            resource_type="task",
            resource_id=str(task.id),
            summary=f"Task '{task.title}' status changed from {old_stat.value} to {tstat.value}",
        )

        logger.info("Task id=%s status updated: %s -> %s", task.id, old_stat.value, tstat.value)
        return saved

    def complete_task(self, task_id: uuid.UUID | str, updated_by: uuid.UUID | str) -> Task:
        """Convenience method to complete a task."""
        return self.update_status(task_id, TaskStatus.COMPLETED, updated_by)

    def cancel_task(self, task_id: uuid.UUID | str, updated_by: uuid.UUID | str) -> Task:
        """Convenience method to cancel a task."""
        return self.update_status(task_id, TaskStatus.CANCELLED, updated_by)

    def add_task_comment(
        self,
        task_id: uuid.UUID | str,
        author_id: uuid.UUID | str,
        author_name: str,
        content: str,
    ) -> Task:
        """Post a comment directly on a task."""
        task = self.repo.get_task(task_id)
        if not task:
            raise ValueError(f"Task with id '{task_id}' not found.")

        self.comment_service.add_comment(
            tenant_id=task.tenant_id,
            workspace_id=task.workspace_id,
            author_id=author_id,
            author_name=author_name,
            resource_type="task",
            resource_id=str(task.id),
            content=content,
            project_id=task.project_id,
        )
        task.comments_count = (getattr(task, "comments_count", 0) or 0) + 1
        return self.repo.update_task(task)

    def list_tasks(
        self,
        tenant_id: uuid.UUID | str,
        workspace_id: uuid.UUID | str,
        project_id: Optional[uuid.UUID | str] = None,
        assigned_to: Optional[uuid.UUID | str] = None,
        status: Optional[TaskStatus | str] = None,
    ) -> List[Task]:
        """Query tasks by workspace and optional filters."""
        tstat = TaskStatus(status) if isinstance(status, str) else status
        return self.repo.list_tasks(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            assigned_to=assigned_to,
            status=tstat,
        )
