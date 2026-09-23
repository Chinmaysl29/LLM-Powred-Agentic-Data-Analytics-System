"""Tests for Phase 12.2 — Enterprise Workspace Management."""

import pytest
from backend.enterprise.multi_tenant import TenantManager, TenantTier
from backend.enterprise.workspace_manager import (
    WorkspaceManager,
    WorkspaceRole,
)


@pytest.fixture(autouse=True)
def reset_managers():
    tm = TenantManager()
    tm.reset()
    wm = WorkspaceManager()
    wm.reset()
    yield
    wm.reset()
    tm.reset()


def test_default_workspace():
    wm = WorkspaceManager()
    ws = wm.get_workspace("ws-system-default")
    assert ws is not None
    assert ws.name == "General Operations"
    assert ws.is_default is True


def test_create_workspace():
    tm = TenantManager()
    wm = WorkspaceManager()
    tenant = tm.create_tenant("Finance Corp", slug="fin-corp")

    ws = wm.create_workspace(
        tenant_id=tenant.id,
        name="FP&A Analytics",
        department="Finance",
        owner_id="user-cfo",
        owner_email="cfo@fincorp.com",
    )
    assert ws.id.startswith("ws-")
    assert ws.department == "Finance"
    assert "user-cfo" in ws.members
    assert ws.members["user-cfo"].role == WorkspaceRole.OWNER


def test_workspace_membership_and_permissions():
    tm = TenantManager()
    wm = WorkspaceManager()
    tenant = tm.create_tenant("Eng Org", slug="eng-org")
    ws = wm.create_workspace(
        tenant_id=tenant.id,
        name="Data Platform",
        department="Engineering",
        owner_id="lead-eng",
    )

    # Add editor and viewer
    wm.add_member(ws.id, user_id="analyst-1", email="a1@eng.com", role=WorkspaceRole.EDITOR)
    wm.add_member(ws.id, user_id="intern-1", email="i1@eng.com", role=WorkspaceRole.VIEWER)

    # Permission checks
    assert wm.check_permission(ws.id, "lead-eng", "manage_members") is True
    assert wm.check_permission(ws.id, "analyst-1", "write") is True
    assert wm.check_permission(ws.id, "analyst-1", "manage_members") is False
    assert wm.check_permission(ws.id, "intern-1", "read") is True
    assert wm.check_permission(ws.id, "intern-1", "write") is False


def test_attach_dataset_and_dashboard():
    tm = TenantManager()
    wm = WorkspaceManager()
    tenant = tm.create_tenant("Retail Co", slug="retail-co")
    ws = wm.create_workspace(
        tenant_id=tenant.id,
        name="Store Operations",
        department="Operations",
        owner_id="ops-mgr",
    )

    wm.attach_dataset(ws.id, "ds-pos-2026")
    wm.attach_dashboard(ws.id, "dash-inventory-turnover")

    summary = wm.get_workspace_analytics(ws.id)
    assert summary["total_datasets"] == 1
    assert summary["total_dashboards"] == 1
    assert summary["total_members"] == 1
