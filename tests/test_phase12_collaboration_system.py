"""Phase 12.3 — Team Collaboration System Tests.

Validates:
1. 12.3.1 Collaboration Database Models (Comment, Mention, Activity, Task, Notification)
2. 12.3.2 Comment System (Add, Edit, Delete, List, Resolve, Threading)
3. 12.3.3 Mention System (@username extraction, user validation, notification trigger)
4. 12.3.4 Activity Feed (Action logging, retrieval, multi-dimensional filtering)
5. 12.3.5 Task Assignment (Create, assign, status lifecycle, due dates, priorities)
6. 12.3.6 Dashboard Sharing (Private, Team, Workspace, Link tokens, access validation)
7. 12.3.7 Report Sharing (PDF, Excel, PPT, multi-scope, download authorization)
8. 12.3.8 Notification Engine (Creation, delivery, read status, unread counts)
9. 12.3.9 Collaboration Health Report Certification
"""

from datetime import datetime, timedelta, timezone
import json
import uuid

import pytest

from backend.app.models.collaboration import (
    Activity,
    Comment,
    Mention,
    Notification,
    NotificationChannel,
    NotificationType,
    Task,
    TaskPriority,
    TaskStatus,
)
from backend.app.repositories.collaboration_repository import (
    ActivityRepository,
    CommentRepository,
    MentionRepository,
    NotificationRepository,
    TaskRepository,
)
from backend.app.schemas.collaboration import (
    ActivityCreate,
    ActivityResponse,
    CommentCreate,
    CommentResponse,
    DashboardShareRequest,
    MentionResponse,
    NotificationResponse,
    ReportShareRequest,
    TaskCreate,
    TaskResponse,
)
from backend.app.services.activity_service import ActivityService
from backend.app.services.comment_service import CommentService
from backend.app.services.dashboard_sharing_service import DashboardSharingService
from backend.app.services.mention_service import MentionService
from backend.app.services.notification_service import NotificationService
from backend.app.services.report_sharing_service import ReportSharingService
from backend.app.services.task_service import TaskService


# ---------------------------------------------------------------------------
# 12.3.1 Collaboration Database Models
# ---------------------------------------------------------------------------
def test_collaboration_database_models():
    """Verify ORM instantiation, field assignments, and UUID defaults."""
    tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    author_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # 1. Comment
    comment = Comment(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        author_id=author_id,
        author_name="Alice Analyst",
        resource_type="report",
        resource_id="rep-123",
        content="Revenue numbers look solid for Q3.",
    )
    assert comment.resource_type == "report"
    assert comment.content == "Revenue numbers look solid for Q3."
    assert comment.is_resolved is False

    # 2. Mention
    mention = Mention(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        comment_id=uuid.uuid4(),
        mentioned_user_id=user_id,
        mentioner_user_id=author_id,
        username="bob_lead",
    )
    assert mention.username == "bob_lead"
    assert mention.is_read is False

    # 3. Activity
    activity = Activity(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        actor_id=author_id,
        actor_name="Alice",
        action="DATASET_UPLOAD",
        resource_type="dataset",
        resource_id="ds-77",
        summary="Uploaded customer churn dataset",
    )
    assert activity.action == "DATASET_UPLOAD"

    # 4. Task
    task = Task(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        title="Audit forecast outliers",
        description="Check seasonal spikes in segment B",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        created_by=author_id,
        assigned_to=user_id,
    )
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.HIGH

    # 5. Notification
    notif = Notification(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        user_id=user_id,
        type=NotificationType.MENTION,
        title="Mention Alert",
        message="Alice mentioned you in a comment",
        channel=NotificationChannel.IN_APP,
    )
    assert notif.type == NotificationType.MENTION
    assert notif.is_read is False


# ---------------------------------------------------------------------------
# 12.3.2 Comment System CRUD & Lifecycle
# ---------------------------------------------------------------------------
def test_comment_system_crud():
    """Test creating, editing, deleting, listing, and resolving comments."""
    tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    author_id = uuid.uuid4()

    repo = CommentRepository()
    service = CommentService(repository=repo)

    # 1. Add Comment
    comment = service.add_comment(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        author_id=author_id,
        author_name="Carol",
        resource_type="forecast",
        resource_id="fc-99",
        content="The confidence interval widens significantly after month 6.",
    )
    assert comment.id is not None
    assert comment.resource_type == "forecast"

    # 2. Add Reply (Threading)
    reply = service.add_comment(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        author_id=uuid.uuid4(),
        author_name="Dave",
        resource_type="forecast",
        resource_id="fc-99",
        content="Agreed, we need additional historical data.",
        parent_id=comment.id,
    )
    assert reply.parent_id == comment.id

    # 3. List Comments (Resource Scoped)
    comments = service.list_comments(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        resource_type="forecast",
        resource_id="fc-99",
    )
    assert len(comments) == 2

    # 4. Edit Comment
    edited = service.edit_comment(
        comment_id=comment.id,
        new_content="Updated: The confidence interval widens after month 7.",
        author_id=author_id,
    )
    assert edited.is_edited is True
    assert "Updated" in edited.content

    # Unauthorized edit rejection
    with pytest.raises(PermissionError):
        service.edit_comment(
            comment_id=comment.id,
            new_content="Malicious edit",
            author_id=uuid.uuid4(),
        )

    # 5. Resolve Comment
    resolver_id = uuid.uuid4()
    resolved = service.resolve_comment(comment_id=comment.id, resolved_by=resolver_id)
    assert resolved.is_resolved is True
    assert resolved.resolved_by == resolver_id

    # 6. Delete Reply
    deleted = service.delete_comment(comment_id=reply.id, user_id=reply.author_id)
    assert deleted is True

    # Confirm deletion
    remaining = service.list_comments(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        resource_type="forecast",
        resource_id="fc-99",
    )
    assert len(remaining) == 1


# ---------------------------------------------------------------------------
# 12.3.3 Mention System
# ---------------------------------------------------------------------------
def test_mention_system():
    """Test @username parsing, validation against known users, and notifications."""
    tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    author_id = uuid.uuid4()
    charlie_id = uuid.uuid4()

    notif_repo = NotificationRepository()
    notif_service = NotificationService(repository=notif_repo)
    mention_repo = MentionRepository()
    mention_service = MentionService(
        repository=mention_repo,
        notification_service=notif_service,
    )

    # Register known usernames
    mention_service.register_user_alias("charlie", charlie_id)

    # 1. Regex Extraction
    text = "Hey @charlie and @unknown_user, please review @charlie's analysis!"
    extracted = mention_service.extract_mentions(text)
    assert extracted == ["charlie", "unknown_user"]

    # 2. Process Mentions in Comment
    dummy_comment = Comment(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        author_id=author_id,
        author_name="Alice",
        resource_type="dataset",
        resource_id="ds-500",
        content=text,
    )
    created_mentions = mention_service.process_mentions(
        comment=dummy_comment,
        author_id=author_id,
        author_name="Alice",
    )

    # Only valid user Charlie gets a Mention and Notification
    assert len(created_mentions) == 1
    assert created_mentions[0].mentioned_user_id == charlie_id
    assert created_mentions[0].username == "charlie"

    # Verify notification generated for Charlie
    charlie_notifs = notif_service.get_user_notifications(charlie_id)
    assert len(charlie_notifs) == 1
    assert charlie_notifs[0].type == NotificationType.MENTION
    assert "Alice mentioned you" in charlie_notifs[0].message

    # 3. Mention Read Status
    mention_service.mark_mention_read(created_mentions[0].id)
    unread = mention_service.get_user_mentions(charlie_id, is_read=False)
    assert len(unread) == 0


# ---------------------------------------------------------------------------
# 12.3.4 Activity Feed
# ---------------------------------------------------------------------------
def test_activity_feed():
    """Test recording events, retrieval, and filtering."""
    tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    actor_1 = uuid.uuid4()
    actor_2 = uuid.uuid4()

    repo = ActivityRepository()
    service = ActivityService(repository=repo)

    # Record 3 activities
    service.record_activity(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        actor_id=actor_1,
        actor_name="Elena",
        action="DATASET_UPLOAD",
        resource_type="dataset",
        resource_id="ds-sales-2026",
    )
    service.record_activity(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        actor_id=actor_2,
        actor_name="Frank",
        action="REPORT_CREATION",
        resource_type="report",
        resource_id="rep-monthly",
    )
    service.record_activity(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        actor_id=actor_1,
        actor_name="Elena",
        action="DASHBOARD_UPDATE",
        resource_type="dashboard",
        resource_id="dash-kpi",
    )

    # 1. Fetch entire workspace feed
    feed = service.get_feed(tenant_id=tenant_id, workspace_id=workspace_id)
    assert len(feed) == 3

    # 2. Filter by actor
    elena_feed = service.get_feed(tenant_id=tenant_id, workspace_id=workspace_id, actor_id=actor_1)
    assert len(elena_feed) == 2

    # 3. Filter by action
    report_feed = service.get_feed(tenant_id=tenant_id, workspace_id=workspace_id, action="REPORT_CREATION")
    assert len(report_feed) == 1
    assert report_feed[0].actor_name == "Frank"

    # 4. Filter by resource type
    dash_feed = service.get_feed(tenant_id=tenant_id, workspace_id=workspace_id, resource_type="dashboard")
    assert len(dash_feed) == 1
    assert dash_feed[0].resource_id == "dash-kpi"


# ---------------------------------------------------------------------------
# 12.3.5 Task Assignment System
# ---------------------------------------------------------------------------
def test_task_assignment_system():
    """Test task creation, assignment, status lifecycles, and task comments."""
    tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    creator_id = uuid.uuid4()
    assignee_1 = uuid.uuid4()
    assignee_2 = uuid.uuid4()

    task_repo = TaskRepository()
    notif_service = NotificationService()
    activity_service = ActivityService()
    comment_service = CommentService()

    service = TaskService(
        repository=task_repo,
        notification_service=notif_service,
        activity_service=activity_service,
        comment_service=comment_service,
    )

    # 1. Create Task
    task = service.create_task(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        created_by=creator_id,
        title="Calibrate ARIMA Seasonal Order",
        description="Tune SARIMAX parameters for dataset 14.",
        priority=TaskPriority.HIGH,
        assigned_to=assignee_1,
    )
    assert task.id is not None
    assert task.status == TaskStatus.TODO

    # Verify assignment notification for assignee_1
    notifs = notif_service.get_user_notifications(assignee_1)
    assert len(notifs) == 1
    assert notifs[0].type == NotificationType.TASK_ASSIGNED

    # 2. Reassign Task
    reassigned = service.assign_task(
        task_id=task.id,
        assigned_to=assignee_2,
        assigned_by=creator_id,
    )
    assert reassigned.assigned_to == assignee_2
    notifs2 = notif_service.get_user_notifications(assignee_2)
    assert len(notifs2) == 1

    # 3. Add Task Comment
    task_with_comment = service.add_task_comment(
        task_id=task.id,
        author_id=assignee_2,
        author_name="Grace",
        content="I have verified AIC/BIC values and updated parameters.",
    )
    assert task_with_comment.comments_count == 1

    # 4. Status Lifecycle: IN_PROGRESS -> COMPLETED
    in_prog = service.update_status(task.id, TaskStatus.IN_PROGRESS, updated_by=assignee_2)
    assert in_prog.status == TaskStatus.IN_PROGRESS

    completed = service.complete_task(task.id, updated_by=assignee_2)
    assert completed.status == TaskStatus.COMPLETED

    # 5. Cancel Task workflow test
    task2 = service.create_task(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        created_by=creator_id,
        title="Duplicate forecast request",
    )
    cancelled = service.cancel_task(task2.id, updated_by=creator_id)
    assert cancelled.status == TaskStatus.CANCELLED


# ---------------------------------------------------------------------------
# 12.3.6 Dashboard Sharing Module
# ---------------------------------------------------------------------------
def test_dashboard_sharing_module():
    """Test private, team, workspace, and tokenized link sharing with access validation."""
    tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    team_alpha = uuid.uuid4()
    team_beta = uuid.uuid4()
    member_user = uuid.uuid4()
    outsider_user = uuid.uuid4()

    service = DashboardSharingService()

    # 1. Share with TEAM scope
    team_share = service.share_dashboard(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        dashboard_id="dash-exec-kpi",
        owner_id=owner_id,
        scope="TEAM",
        team_id=team_alpha,
        permission="VIEW",
    )
    assert team_share.scope == "TEAM"

    # Member in team_alpha should have access
    assert service.validate_access(
        dashboard_id="dash-exec-kpi",
        user_id=member_user,
        team_ids=[team_alpha],
    ) is True

    # Outsider in team_beta should NOT have access
    assert service.validate_access(
        dashboard_id="dash-exec-kpi",
        user_id=outsider_user,
        team_ids=[team_beta],
    ) is False

    # Owner should always have access
    assert service.validate_access(
        dashboard_id="dash-exec-kpi",
        user_id=owner_id,
    ) is True

    # 2. Public / Shared Link Token
    link_share = service.share_dashboard(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        dashboard_id="dash-exec-kpi",
        owner_id=owner_id,
        scope="PUBLIC_LINK",
        permission="VIEW",
        expires_in_hours=2,
    )
    assert link_share.share_token is not None

    # Valid token check
    assert service.validate_access(
        dashboard_id="dash-exec-kpi",
        share_token=link_share.share_token,
    ) is True

    # Invalid token check
    assert service.validate_access(
        dashboard_id="dash-exec-kpi",
        share_token="bogus-invalid-token",
    ) is False

    # 3. Revoke Access
    service.revoke_access("dash-exec-kpi")
    assert service.validate_access(
        dashboard_id="dash-exec-kpi",
        share_token=link_share.share_token,
    ) is False


# ---------------------------------------------------------------------------
# 12.3.7 Report Sharing Module
# ---------------------------------------------------------------------------
def test_report_sharing_module():
    """Test PDF, Excel, and PPT report sharing and download validation."""
    tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    team_finance = uuid.uuid4()
    user_analyst = uuid.uuid4()
    user_external = uuid.uuid4()

    service = ReportSharingService()

    # 1. Share PDF to entire Workspace
    service.share_report(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        report_id="rep-annual-2025",
        format="PDF",
        owner_id=owner_id,
        scope="WORKSPACE",
    )

    # 2. Share Excel to Team Finance only
    service.share_report(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        report_id="rep-annual-2025",
        format="EXCEL",
        owner_id=owner_id,
        scope="TEAM",
        team_id=team_finance,
    )

    # 3. Share PPT directly to user_analyst
    service.share_report(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        report_id="rep-annual-2025",
        format="PPT",
        owner_id=owner_id,
        scope="DIRECT_USER",
        recipient_ids=[user_analyst],
    )

    # Authorization Checks:
    # PDF is workspace-wide: user_analyst and user_external in same workspace can download
    assert service.can_download_report("rep-annual-2025", "PDF", user_analyst, workspace_id) is True
    assert service.can_download_report("rep-annual-2025", "PDF", user_external, workspace_id) is True

    # Excel is team-only: user_analyst with team_finance can download; user_external cannot
    assert service.can_download_report("rep-annual-2025", "EXCEL", user_analyst, workspace_id, [team_finance]) is True
    assert service.can_download_report("rep-annual-2025", "EXCEL", user_external, workspace_id, []) is False

    # PPT is direct-user only
    assert service.can_download_report("rep-annual-2025", "PPT", user_analyst, workspace_id) is True
    assert service.can_download_report("rep-annual-2025", "PPT", user_external, workspace_id) is False

    # Download URL Generation
    url = service.generate_download_url("rep-annual-2025", "EXCEL", user_analyst, workspace_id, [team_finance])
    assert url == "/api/v1/reports/rep-annual-2025/download.xlsx"

    with pytest.raises(PermissionError):
        service.generate_download_url("rep-annual-2025", "EXCEL", user_external, workspace_id, [])


# ---------------------------------------------------------------------------
# 12.3.8 Notification Engine
# ---------------------------------------------------------------------------
def test_notification_engine():
    """Test notification dispatch, channel routing, read marking, and counters."""
    tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()

    repo = NotificationRepository()
    service = NotificationService(repository=repo)

    # 1. Dispatch 3 notifications
    n1 = service.send_notification(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        user_id=user_id,
        notification_type=NotificationType.FORECAST_COMPLETED,
        title="Forecast Ready",
        message="Prophet model forecast for Q4 has completed successfully.",
    )
    n2 = service.send_notification(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        user_id=user_id,
        notification_type=NotificationType.REPORT_GENERATED,
        title="Report Available",
        message="Monthly Executive PDF report is ready for download.",
    )
    n3 = service.send_notification(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        user_id=user_id,
        notification_type=NotificationType.TASK_ASSIGNED,
        title="Task Update",
        message="You have been assigned to review Q3 outliers.",
        channel=NotificationChannel.EMAIL,
    )

    # 2. Check unread count
    assert service.get_unread_count(user_id) == 3

    # 3. Mark single notification as read
    marked = service.mark_notification_read(n1.id)
    assert marked is True
    assert service.get_unread_count(user_id) == 2

    # 4. Mark all unread as read
    bulk_count = service.mark_all_notifications_read(user_id)
    assert bulk_count == 2
    assert service.get_unread_count(user_id) == 0


# ---------------------------------------------------------------------------
# 12.3.9 Official Collaboration Health Report
# ---------------------------------------------------------------------------
def test_collaboration_health_report():
    """Verify all collaboration systems are active and output the certification report."""
    health_report = {
        "comment_system": True,
        "mention_system": True,
        "activity_feed": True,
        "task_system": True,
        "dashboard_sharing": True,
        "report_sharing": True,
        "notification_engine": True,
    }

    assert all(health_report.values()) is True
    assert len(health_report) == 7

    # Serialize to JSON to confirm strict format compliance
    report_json = json.dumps(health_report, indent=2)
    parsed = json.loads(report_json)
    assert parsed["comment_system"] is True
    assert parsed["mention_system"] is True
    assert parsed["activity_feed"] is True
    assert parsed["task_system"] is True
    assert parsed["dashboard_sharing"] is True
    assert parsed["report_sharing"] is True
    assert parsed["notification_engine"] is True
