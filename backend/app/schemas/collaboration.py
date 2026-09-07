"""Phase 12.3 — Collaboration Schemas.

Pydantic schemas for Comments, Mentions, Activities, Tasks, Notifications,
and Resource Sharing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.collaboration import (
    NotificationChannel,
    NotificationType,
    TaskPriority,
    TaskStatus,
)


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    resource_type: str = Field(..., description="'report', 'dashboard', 'dataset', 'forecast'")
    resource_id: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None


class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    is_resolved: Optional[bool] = None


class CommentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    author_id: uuid.UUID
    author_name: str
    resource_type: str
    resource_id: str
    content: str
    parent_id: Optional[uuid.UUID] = None
    is_edited: bool = False
    is_resolved: bool = False
    resolved_by: Optional[uuid.UUID] = None
    resolved_at: Optional[datetime] = None
    mentions: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentListResponse(BaseModel):
    total: int
    items: List[CommentResponse]


# ---------------------------------------------------------------------------
# Mentions
# ---------------------------------------------------------------------------
class MentionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    comment_id: uuid.UUID
    mentioned_user_id: uuid.UUID
    mentioner_user_id: uuid.UUID
    username: str
    is_read: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MentionListResponse(BaseModel):
    total: int
    items: List[MentionResponse]


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------
class ActivityCreate(BaseModel):
    action: str = Field(..., description="'DATASET_UPLOAD', 'ANALYSIS_CREATION', etc.")
    resource_type: str
    resource_id: str
    summary: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


class ActivityResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    actor_id: uuid.UUID
    actor_name: str
    action: str
    resource_type: str
    resource_id: str
    summary: str
    details: Dict[str, Any]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityFeedResponse(BaseModel):
    total: int
    items: List[ActivityResponse]


class ActivityFilter(BaseModel):
    actor_id: Optional[uuid.UUID] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    project_id: Optional[uuid.UUID] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None
    created_by: uuid.UUID
    comments_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    total: int
    items: List[TaskResponse]


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
class NotificationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    channel: NotificationChannel
    is_read: bool = False
    read_at: Optional[datetime] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    items: List[NotificationResponse]


class NotificationMarkReadRequest(BaseModel):
    notification_ids: Optional[List[uuid.UUID]] = None
    all_unread: bool = False


# ---------------------------------------------------------------------------
# Resource Sharing
# ---------------------------------------------------------------------------
class DashboardShareRequest(BaseModel):
    scope: str = Field("WORKSPACE", description="'PRIVATE', 'TEAM', 'WORKSPACE', 'PUBLIC_LINK'")
    team_id: Optional[uuid.UUID] = None
    permission: str = Field("VIEW", description="'VIEW' or 'EDIT'")
    expires_in_hours: Optional[int] = None


class DashboardShareResponse(BaseModel):
    dashboard_id: str
    scope: str
    permission: str
    share_token: Optional[str] = None
    share_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class ReportShareRequest(BaseModel):
    format: str = Field("PDF", description="'PDF', 'EXCEL', 'PPT'")
    scope: str = Field("WORKSPACE", description="'WORKSPACE', 'TEAM', 'DIRECT_USER'")
    recipient_ids: List[uuid.UUID] = Field(default_factory=list)
    permission: str = Field("DOWNLOAD", description="'VIEW', 'DOWNLOAD', 'EXPORT'")


class ReportShareResponse(BaseModel):
    report_id: str
    format: str
    scope: str
    permission: str
    download_url: str
    expires_at: Optional[datetime] = None
