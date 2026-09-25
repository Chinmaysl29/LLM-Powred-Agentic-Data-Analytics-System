"""Tests for Phase 12.1 — Multi-Tenant Architecture."""

import pytest
from backend.enterprise.multi_tenant import (
    TenantManager,
    TenantTier,
    TenantStatus,
    TenantQuota,
    get_current_tenant_id,
    set_current_tenant_id,
    tenant_context,
    generate_rls_sql_policies,
    verify_tenant_access,
)


@pytest.fixture(autouse=True)
def reset_tenant_manager():
    mgr = TenantManager()
    mgr.reset()
    yield
    mgr.reset()


def test_default_system_tenant():
    mgr = TenantManager()
    system_tenant = mgr.get_tenant("system")
    assert system_tenant is not None
    assert system_tenant.name == "System Default"
    assert system_tenant.status == TenantStatus.ACTIVE
    assert system_tenant.tier == TenantTier.UNLIMITED


def test_create_and_get_tenant():
    mgr = TenantManager()
    tenant = mgr.create_tenant(
        name="Acme Corporation",
        slug="acme-corp",
        tier=TenantTier.ENTERPRISE,
        admin_email="admin@acme.com",
    )
    assert tenant.id is not None
    assert tenant.name == "Acme Corporation"
    assert tenant.slug == "acme-corp"
    assert tenant.tier == TenantTier.ENTERPRISE

    # Retrieve by ID
    fetched = mgr.get_tenant(tenant.id)
    assert fetched is not None
    assert fetched.name == "Acme Corporation"

    # Retrieve by slug
    fetched_slug = mgr.get_tenant_by_slug("acme-corp")
    assert fetched_slug is not None
    assert fetched_slug.id == tenant.id


def test_duplicate_slug_rejection():
    mgr = TenantManager()
    mgr.create_tenant(name="Duplicate Co", slug="dup-slug")
    with pytest.raises(ValueError, match="already exists"):
        mgr.create_tenant(name="Duplicate Co 2", slug="dup-slug")


def test_tenant_context_manager():
    assert get_current_tenant_id() == "system"

    with tenant_context("tenant-abc-123"):
        assert get_current_tenant_id() == "tenant-abc-123"

    # Restores context afterwards
    assert get_current_tenant_id() == "system"


def test_quota_checking_and_usage_tracking():
    mgr = TenantManager()
    tenant = mgr.create_tenant(name="Small Business", tier=TenantTier.FREE)

    # Free tier has max 5 datasets
    check = mgr.check_quota(tenant.id, "datasets", requested=2)
    assert check["allowed"] is True
    assert check["limit"] == 5

    # Record 4 datasets
    mgr.record_usage(tenant.id, "datasets", delta=4)
    # Requesting 2 more should fail (4 + 2 = 6 > 5)
    check_exceeded = mgr.check_quota(tenant.id, "datasets", requested=2)
    assert check_exceeded["allowed"] is False
    assert "Quota exceeded" in check_exceeded["reason"]


def test_tenant_status_transitions():
    mgr = TenantManager()
    tenant = mgr.create_tenant(name="Payment Lapsed Org")
    assert tenant.status == TenantStatus.ACTIVE

    mgr.update_tenant_status(tenant.id, TenantStatus.SUSPENDED, reason="Overdue billing")
    assert tenant.status == TenantStatus.SUSPENDED

    # Quota check should be blocked for suspended tenant
    quota_check = mgr.check_quota(tenant.id, "users", requested=1)
    assert quota_check["allowed"] is False
    assert "suspended" in quota_check["reason"]


def test_generate_rls_sql_policies():
    ddl_statements = generate_rls_sql_policies("datasets", tenant_col="tenant_id")
    assert len(ddl_statements) == 5
    assert any("ENABLE ROW LEVEL SECURITY" in s for s in ddl_statements)
    assert any("current_setting('app.current_tenant_id'" in s for s in ddl_statements)


def test_verify_tenant_access():
    # System super-admin access
    assert verify_tenant_access("system", "tenant-xyz") is True

    # Same tenant
    assert verify_tenant_access("tenant-1", "tenant-1") is True

    # Different tenants
    assert verify_tenant_access("tenant-1", "tenant-2") is False
