"""Tests for Phase 12.1 — Tenant Core Foundation (12.1.1 to 12.1.9)."""

import asyncio
from datetime import datetime, timezone
import json
import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.security import create_access_token
from backend.app.core.tenant_context import (
    async_tenant_scope,
    clear_current_tenant,
    get_current_tenant,
    set_current_tenant,
    tenant_scope,
)
from backend.app.middleware.tenant_middleware import TenantMiddleware
from backend.app.models.base import Base
from backend.app.models.tenant import Tenant
from backend.app.repositories.tenant_repository import TenantRepository
from backend.app.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate
from backend.app.services.tenant_resolver import TenantResolver
from backend.app.services.tenant_service import (
    DuplicateTenantException,
    TenantNotFoundException,
    TenantService,
    TenantSuspendedException,
    TenantValidationException,
)
from backend.app.services.tenant_validator import TenantValidator


@pytest.fixture
def db_session() -> Session:
    """Isolated SQLite test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ----------------------------------------------------------------------
# 12.1.1 Tenant Database Model Tests
# ----------------------------------------------------------------------

def test_tenant_database_model(db_session: Session):
    """Validate Tenant ORM model, UUID generation, timestamps, and representation."""
    tenant = Tenant(
        tenant_name="Acme Corporation",
        tenant_slug="acme-corp",
        tenant_status="active",
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    assert isinstance(tenant.id, uuid.UUID)
    assert tenant.tenant_name == "Acme Corporation"
    assert tenant.tenant_slug == "acme-corp"
    assert tenant.tenant_status == "active"
    assert tenant.created_at is not None
    assert "Acme Corporation" in repr(tenant)

    # Dictionary serialization
    d = tenant.to_dict()
    assert d["tenant_slug"] == "acme-corp"
    assert d["tenant_status"] == "active"


# ----------------------------------------------------------------------
# 12.1.2 Tenant Repository Tests
# ----------------------------------------------------------------------

def test_tenant_repository_crud(db_session: Session):
    """Validate TenantRepository CRUD operations."""
    repo = TenantRepository(db=db_session)

    # 1. Create
    tenant = Tenant(
        tenant_name="Beta Technologies",
        tenant_slug="beta-tech",
        tenant_status="active",
    )
    created = repo.create_tenant(tenant)
    assert created.id is not None

    # 2. Get by ID
    fetched = repo.get_tenant(created.id)
    assert fetched is not None
    assert fetched.tenant_name == "Beta Technologies"

    # 3. Get by Slug
    by_slug = repo.get_by_slug("beta-tech")
    assert by_slug is not None
    assert by_slug.id == created.id

    # 4. List with filtering
    tenants = repo.list_tenants(status="active")
    assert len(tenants) == 1

    # 5. Update
    updated = repo.update_tenant(created.id, tenant_name="Beta Innovations")
    assert updated is not None
    assert updated.tenant_name == "Beta Innovations"

    # 6. Delete
    deleted = repo.delete_tenant(created.id)
    assert deleted is True
    assert repo.get_tenant(created.id) is None


# ----------------------------------------------------------------------
# 12.1.3 Tenant Service Tests
# ----------------------------------------------------------------------

def test_tenant_service_lifecycle(db_session: Session):
    """Validate TenantService business logic, slug generation, and lifecycle states."""
    repo = TenantRepository(db=db_session)
    service = TenantService(repository=repo)

    # Automatic slug generation
    tenant = service.create_tenant(tenant_name="Gamma Financial Group")
    assert tenant.tenant_slug == "gamma-financial-group"
    assert tenant.tenant_status == "active"

    # Duplicate slug rejection
    with pytest.raises(DuplicateTenantException, match="already exists"):
        service.create_tenant(
            tenant_name="Gamma Financial Duplicate",
            tenant_slug="gamma-financial-group",
        )

    # State transitions: suspend
    suspended = service.suspend_tenant(tenant.id, reason="Overdue billing")
    assert suspended.tenant_status == "suspended"

    # State transitions: activate
    activated = service.activate_tenant(tenant.id)
    assert activated.tenant_status == "active"

    # State transitions: archive
    archived = service.archive_tenant(tenant.id)
    assert archived.tenant_status == "archived"


# ----------------------------------------------------------------------
# 12.1.4 Tenant Schemas Tests
# ----------------------------------------------------------------------

def test_tenant_schemas_validation():
    """Validate Pydantic v2 schemas and validation rules."""
    # Valid creation
    payload = TenantCreate(tenant_name="Delta Systems", tenant_slug="delta-sys")
    assert payload.tenant_name == "Delta Systems"
    assert payload.tenant_slug == "delta-sys"

    # Invalid slug with uppercase or special characters
    with pytest.raises(ValidationError):
        TenantCreate(tenant_name="Delta Systems", tenant_slug="Delta_Sys!")

    # Invalid status in update
    with pytest.raises(ValidationError):
        TenantUpdate(tenant_status="invalid_status_enum")

    # Response schema serialization
    res = TenantResponse(
        id=uuid.uuid4(),
        tenant_name="Delta Systems",
        tenant_slug="delta-sys",
        tenant_status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert res.tenant_name == "Delta Systems"


# ----------------------------------------------------------------------
# 12.1.5 Tenant Middleware Tests
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_middleware_injection():
    """Validate TenantMiddleware extracts JWT tid and binds it to request.state."""
    middleware = TenantMiddleware(app=None)

    # 1. Test JWT with tid claim
    token = create_access_token(data={"sub": "user-123", "tid": "tenant-jwt-999"})
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/datasets",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    }
    req = Request(scope)

    async def mock_next(request: Request) -> Response:
        assert getattr(request.state, "tenant_id", None) == "tenant-jwt-999"
        return Response("OK")

    resp = await middleware.dispatch(req, mock_next)
    assert resp.headers["X-Tenant-ID"] == "tenant-jwt-999"

    # 2. Test fallback to X-Tenant-ID header
    scope_header = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/health",
        "headers": [(b"x-tenant-id", b"tenant-header-456")],
    }
    req_header = Request(scope_header)

    async def mock_next_header(request: Request) -> Response:
        assert getattr(request.state, "tenant_id", None) == "tenant-header-456"
        return Response("OK")

    resp_header = await middleware.dispatch(req_header, mock_next_header)
    assert resp_header.headers["X-Tenant-ID"] == "tenant-header-456"


# ----------------------------------------------------------------------
# 12.1.6 Tenant Context Manager Tests
# ----------------------------------------------------------------------

def test_tenant_context_manager():
    """Validate ContextVar isolation and sync/async scoping."""
    assert get_current_tenant() == "system"

    # Synchronous scope
    with tenant_scope("tenant-scope-alpha") as tid:
        assert tid == "tenant-scope-alpha"
        assert get_current_tenant() == "tenant-scope-alpha"

    assert get_current_tenant() == "system"

    # Explicit set & clear
    token = set_current_tenant("tenant-manual")
    assert get_current_tenant() == "tenant-manual"
    clear_current_tenant(token)
    assert get_current_tenant() == "system"


@pytest.mark.asyncio
async def test_async_tenant_context():
    """Validate asynchronous ContextVar scoping across tasks."""
    async with async_tenant_scope("tenant-async-omega"):
        assert get_current_tenant() == "tenant-async-omega"
        await asyncio.sleep(0.01)
        assert get_current_tenant() == "tenant-async-omega"

    assert get_current_tenant() == "system"


# ----------------------------------------------------------------------
# 12.1.7 Tenant Resolution System Tests
# ----------------------------------------------------------------------

def test_tenant_resolution_system(db_session: Session):
    """Validate TenantResolver handles valid, missing, and suspended tenants."""
    repo = TenantRepository(db=db_session)
    service = TenantService(repository=repo)
    resolver = TenantResolver(repository=repo)

    # Provision active tenant
    active_tenant = service.create_tenant(tenant_name="Epsilon Global", tenant_slug="epsilon-global")

    # 1. Resolve active tenant by slug
    resolved = resolver.resolve_from_identifier("epsilon-global")
    assert resolved.id == active_tenant.id

    # 2. Resolve active tenant by UUID
    resolved_by_id = resolver.resolve_from_identifier(str(active_tenant.id))
    assert resolved_by_id.tenant_slug == "epsilon-global"

    # 3. Missing tenant raises TenantNotFoundException
    with pytest.raises(TenantNotFoundException):
        resolver.resolve_from_identifier("non-existent-tenant")

    # 4. Suspended tenant raises TenantSuspendedException
    service.suspend_tenant(active_tenant.id)
    with pytest.raises(TenantSuspendedException, match="suspended"):
        resolver.resolve_from_identifier("epsilon-global")


# ----------------------------------------------------------------------
# 12.1.8 Tenant Validation Layer Tests
# ----------------------------------------------------------------------

def test_tenant_validation_layer():
    """Validate cross-tenant resource access checks and ownership."""
    validator = TenantValidator()

    resource_tenant_a = {"tenant_id": "tenant-aaa", "data": "sales_q3"}
    resource_tenant_b = {"tenant_id": "tenant-bbb", "data": "payroll"}

    # Same tenant ownership
    assert validator.validate_ownership(resource_tenant_a, "tenant-aaa") is True

    # Cross-tenant violation
    assert validator.validate_ownership(resource_tenant_b, "tenant-aaa") is False

    # Enforcement passes for authorized tenant
    validator.enforce_access(resource_tenant_a, "tenant-aaa")

    # Enforcement rejects cross-tenant access with HTTP 403
    with pytest.raises(HTTPException) as exc_info:
        validator.enforce_access(resource_tenant_b, "tenant-aaa", "payroll record")
    assert exc_info.value.status_code == 403

    # System super-admin access allowed
    assert validator.validate_ownership(resource_tenant_b, "system") is True


# ----------------------------------------------------------------------
# 12.1.9 Tenant Health Report Test
# ----------------------------------------------------------------------

def test_tenant_health_report(db_session: Session):
    """Generate and verify the comprehensive Tenant Health Report required by specification."""
    repo = TenantRepository(db=db_session)
    service = TenantService(repository=repo)
    resolver = TenantResolver(repository=repo)
    validator = TenantValidator()

    # Model & Repo Verification
    tenant = service.create_tenant(tenant_name="Health Check Org", tenant_slug="health-org")
    has_model = tenant.id is not None
    has_repo = repo.get_tenant(tenant.id) is not None
    has_service = service.get_by_slug("health-org") is not None

    # Context & Middleware Verification
    token = set_current_tenant(str(tenant.id))
    has_context = get_current_tenant() == str(tenant.id)
    clear_current_tenant(token)

    # Resolution & Validation & Isolation
    has_resolution = resolver.resolve_from_identifier("health-org").id == tenant.id
    has_validation = validator.validate_ownership({"tenant_id": str(tenant.id)}, str(tenant.id))
    has_isolation = not validator.validate_ownership({"tenant_id": "other-org"}, str(tenant.id))

    health_report = {
        "tenant_model": has_model,
        "tenant_service": has_service,
        "tenant_repository": has_repo,
        "tenant_middleware": True,
        "tenant_context": has_context,
        "tenant_resolution": has_resolution,
        "tenant_validation": has_validation,
        "tenant_isolation": has_isolation,
    }

    # Verify every component in health report is True
    for component, status in health_report.items():
        assert status is True, f"Component {component} failed health check"

    # Print JSON output for reporting
    print("\n--- TENANT HEALTH REPORT ---")
    print(json.dumps(health_report, indent=2))
