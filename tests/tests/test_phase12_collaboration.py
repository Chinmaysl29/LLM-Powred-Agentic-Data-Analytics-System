"""Tests for Phase 12.3 — Team Collaboration System."""

import pytest
from backend.enterprise.collaboration import (
    CollaborationManager,
)


@pytest.fixture(autouse=True)
def reset_collab():
    cm = CollaborationManager()
    cm.reset()
    yield
    cm.reset()


def test_add_and_list_comments_with_mentions():
    cm = CollaborationManager()
    comment = cm.add_comment(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        target_type="dataset",
        target_id="ds-q3-sales",
        author_id="usr-1",
        author_name="Alice",
        content="Great numbers! Hey @bob and @carol.smith, can you verify column 4?",
    )
    assert comment.id.startswith("cmt-")
    assert "bob" in comment.mentions
    assert "carol.smith" in comment.mentions

    comments = cm.list_comments(target_type="dataset", target_id="ds-q3-sales")
    assert len(comments) == 1
    assert comments[0].author_name == "Alice"


def test_resolve_comment_thread():
    cm = CollaborationManager()
    c1 = cm.add_comment(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        target_type="report",
        target_id="rep-101",
        author_id="usr-1",
        author_name="Alice",
        content="Is the currency USD or EUR?",
    )
    c2 = cm.add_comment(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        target_type="report",
        target_id="rep-101",
        author_id="usr-2",
        author_name="Bob",
        content="It is USD.",
        thread_id=c1.id,
    )
    assert c1.resolved is False

    resolved_count = cm.resolve_thread(c1.id, resolved_by_id="usr-1")
    assert resolved_count == 2

    # Listing unresolved should return 0
    unresolved = cm.list_comments("report", "rep-101", include_resolved=False)
    assert len(unresolved) == 0


def test_shared_templates_and_usage():
    cm = CollaborationManager()
    tmpl = cm.create_template(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        title="Monthly Churn Rate SQL",
        sql_or_prompt="SELECT date_trunc('month', date), count(*) FROM churn GROUP BY 1;",
        author_id="usr-analyst",
        author_name="Dave",
        tags=["churn", "retention", "sql"],
    )
    assert tmpl.usage_count == 0

    cm.use_template(tmpl.id)
    assert tmpl.usage_count == 1

    by_tag = cm.list_templates(tenant_id="tenant-1", tag="churn")
    assert len(by_tag) == 1


def test_activity_feed_and_bookmarks():
    cm = CollaborationManager()
    cm.record_activity(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        user_id="usr-1",
        user_name="Alice",
        action="CREATED",
        target_type="DASHBOARD",
        target_id="dash-kpi",
        summary="Alice created executive KPI dashboard",
    )

    feed = cm.get_activity_feed(tenant_id="tenant-1")
    assert len(feed) >= 1
    assert feed[0].action == "CREATED"

    # Save bookmark
    bm = cm.save_bookmark(
        tenant_id="tenant-1",
        workspace_id="ws-1",
        user_id="usr-1",
        name="Q3 High Risk Cohort",
        state_payload={"filter_region": "EU", "risk_score_gt": 0.8},
        is_shared=True,
    )
    assert bm.id.startswith("bm-")
    bookmarks = cm.list_bookmarks(tenant_id="tenant-1", workspace_id="ws-1", user_id="usr-2")
    assert len(bookmarks) == 1  # visible because is_shared=True
