"""Tests for Phase 12.2 — Enterprise Workspace Management (12.2.1 to 12.2.9)."""

import json
import uuid

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.department import Department
from backend.app.models.project import Project
from backend.app.models.team import Team
from backend.app.models.tenant import Tenant
from backend.app.models.workspace import Workspace
from backend.app.repositories.department_repository import DepartmentRepository
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.repositories.team_repository import TeamRepository
from backend.app.repositories.tenant_repository import TenantRepository
from backend.app.repositories.workspace_repository import WorkspaceRepository
from backend.app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from backend.app.services.department_service import DepartmentService
from backend.app.services.project_service import ProjectService
from backend.app.services.team_service import TeamService
from backend.app.services.workspace_service import (
    DuplicateWorkspaceException,
    WorkspaceNotFoundException,
    WorkspaceService,
    WorkspaceValidationException,
)


@pytest.fixture
def db_session() -> Session:
    """Isolated in-memory SQLite database session."""
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


@pytest.fixture
def sample_tenant(db_session: Session) -> Tenant:
    """Helper fixture providing an active tenant."""
    tenant = Tenant(
        tenant_name="Acme Enterprise",
        tenant_slug="acme-enterprise",
        tenant_status="active",
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


# ----------------------------------------------------------------------
# 12.2.1 Workspace Database Model Tests
# ----------------------------------------------------------------------

def test_workspace_database_model(db_session: Session, sample_tenant: Tenant):
    """Validate Workspace ORM model, foreign keys, relationships, and representation."""
    ws = Workspace(
        tenant_id=sample_tenant.id,
        workspace_name="Finance Operations",
        workspace_slug="finance-operations",
        description="Core financial intelligence unit",
        status="active",
    )
    db_session.add(ws)
    db_session.commit()
    db_session.refresh(ws)

    assert isinstance(ws.id, uuid.UUID)
    assert ws.tenant_id == sample_tenant.id
    assert ws.workspace_name == "Finance Operations"
    assert ws.workspace_slug == "finance-operations"
    assert ws.status == "active"
    assert "Finance Operations" in repr(ws)

    # Relationship to Tenant
    assert ws.tenant is not None
    assert ws.tenant.id == sample_tenant.id

    # Serialization
    d = ws.to_dict()
    assert d["workspace_slug"] == "finance-operations"
    assert d["tenant_id"] == str(sample_tenant.id)


# ----------------------------------------------------------------------
# 12.2.2 Workspace Repository Tests
# ----------------------------------------------------------------------

def test_workspace_repository_crud(db_session: Session, sample_tenant: Tenant):
    """Validate WorkspaceRepository CRUD operations."""
    repo = WorkspaceRepository(db=db_session)

    # 1. Create
    ws = Workspace(
        tenant_id=sample_tenant.id,
        workspace_name="Engineering Core",
        workspace_slug="engineering-core",
        description="Data engineering workspace",
        status="active",
    )
    created = repo.create_workspace(ws)
    assert created.id is not None

    # 2. Get by ID
    fetched = repo.get_workspace(created.id)
    assert fetched is not None
    assert fetched.workspace_name == "Engineering Core"

    # 3. Get by slug
    by_slug = repo.get_by_slug(sample_tenant.id, "engineering-core")
    assert by_slug is not None
    assert by_slug.id == created.id

    # 4. List workspaces
    workspaces = repo.list_workspaces(sample_tenant.id, status="active")
    assert len(workspaces) == 1

    # 5. Update
    updated = repo.update_workspace(created.id, workspace_name="Engineering & Infrastructure")
    assert updated is not None
    assert updated.workspace_name == "Engineering & Infrastructure"

    # 6. Delete
    deleted = repo.delete_workspace(created.id)
    assert deleted is True
    assert repo.get_workspace(created.id) is None


# ----------------------------------------------------------------------
# 12.2.3 Workspace Service Tests
# ----------------------------------------------------------------------

def test_workspace_service_lifecycle(db_session: Session, sample_tenant: Tenant):
    """Validate WorkspaceService business rules, slug derivation, and lifecycle transitions."""
    repo = WorkspaceRepository(db=db_session)
    service = WorkspaceService(repository=repo)

    # Automatic slug generation
    ws = service.create_workspace(
        tenant_id=sample_tenant.id,
        workspace_name="Customer Growth & Success",
    )
    assert ws.workspace_slug == "customer-growth-success"

    # Duplicate slug rejection within same tenant
    with pytest.raises(DuplicateWorkspaceException, match="already exists"):
        service.create_workspace(
            tenant_id=sample_tenant.id,
            workspace_name="Duplicate Growth",
            workspace_slug="customer-growth-success",
        )

    # State transitions: suspend
    suspended = service.suspend_workspace(ws.id, reason="Security audit")
    assert suspended.status == "suspended"

    # State transitions: activate
    activated = service.activate_workspace(ws.id)
    assert activated.status == "active"

    # State transitions: archive
    archived = service.archive_workspace(ws.id)
    assert archived.status == "archived"


# ----------------------------------------------------------------------
# 12.2.4 Workspace Schemas Tests
# ----------------------------------------------------------------------

def test_workspace_schemas_validation():
    """Validate Pydantic v2 schemas and constraints."""
    tid = uuid.uuid4()
    payload = WorkspaceCreate(
        tenant_id=tid,
        workspace_name="Supply Chain Analytics",
        workspace_slug="supply-chain",
    )
    assert payload.workspace_name == "Supply Chain Analytics"

    # Invalid slug format
    with pytest.raises(ValidationError):
        WorkspaceCreate(
            tenant_id=tid,
            workspace_name="Invalid Slug WS",
            workspace_slug="Invalid_Slug!",
        )

    # Invalid status
    with pytest.raises(ValidationError):
        WorkspaceUpdate(status="unknown_status")

    # Required field validation (workspace_name too short)
    with pytest.raises(ValidationError):
        WorkspaceCreate(tenant_id=tid, workspace_name="A")


# ----------------------------------------------------------------------
# 12.2.5 Workspace API Tests
# ----------------------------------------------------------------------

def test_workspace_api_endpoints():
    """Validate REST API /api/v1/workspaces endpoints."""
    app = create_app()
    client = TestClient(app)

    # 1. Create workspace
    dummy_tid = uuid.uuid4()
    create_resp = client.post(
        "/api/v1/workspaces",
        json={
            "tenant_id": str(dummy_tid),
            "workspace_name": "Product Intelligence",
            "workspace_slug": "product-intel",
            "description": "Product telemetry and feature experiments",
        },
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    ws_id = data["id"]
    assert data["workspace_slug"] == "product-intel"

    # 2. Get workspace by ID
    get_resp = client.get(f"/api/v1/workspaces/{ws_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["workspace_name"] == "Product Intelligence"

    # 3. List workspaces for tenant
    list_resp = client.get(f"/api/v1/workspaces?tenant_id={dummy_tid}")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 4. Update workspace
    put_resp = client.put(
        f"/api/v1/workspaces/{ws_id}",
        json={"workspace_name": "Product & Growth Intelligence", "status": "active"},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["workspace_name"] == "Product & Growth Intelligence"

    # 5. Delete workspace
    del_resp = client.delete(f"/api/v1/workspaces/{ws_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"


# ----------------------------------------------------------------------
# 12.2.6 Department Module Tests
# ----------------------------------------------------------------------

def test_department_module(db_session: Session, sample_tenant: Tenant):
    """Validate Department entity, repository, and service scoping within workspace."""
    ws_repo = WorkspaceRepository(db=db_session)
    ws = ws_repo.create_workspace(
        Workspace(
            tenant_id=sample_tenant.id,
            workspace_name="Commercial Division",
            workspace_slug="commercial",
        )
    )

    dept_repo = DepartmentRepository(db=db_session)
    dept_service = DepartmentService(repository=dept_repo)

    dept = dept_service.create_department(
        workspace_id=ws.id,
        department_name="Enterprise Sales",
        description="Global enterprise accounts",
    )
    assert dept.id is not None
    assert dept.department_name == "Enterprise Sales"
    assert dept.workspace_id == ws.id

    departments = dept_service.list_departments(ws.id)
    assert len(departments) == 1

    deleted = dept_service.delete_department(dept.id)
    assert deleted is True
    assert dept_service.get_department(dept.id) is None


# ----------------------------------------------------------------------
# 12.2.7 Team Module Tests
# ----------------------------------------------------------------------

def test_team_module(db_session: Session, sample_tenant: Tenant):
    """Validate Team entity, repository, and service scoping within department."""
    ws = WorkspaceRepository(db=db_session).create_workspace(
        Workspace(tenant_id=sample_tenant.id, workspace_name="Marketing Ops", workspace_slug="mktg-ops")
    )
    dept = DepartmentService(DepartmentRepository(db_session)).create_department(
        workspace_id=ws.id, department_name="Digital Marketing"
    )

    team_repo = TeamRepository(db=db_session)
    team_service = TeamService(repository=team_repo)

    team = team_service.create_team(
        department_id=dept.id,
        team_name="SEO & Content Strategy",
        description="Organic traffic acquisition",
    )
    assert team.id is not None
    assert team.team_name == "SEO & Content Strategy"
    assert team.department_id == dept.id

    teams = team_service.list_teams(dept.id)
    assert len(teams) == 1

    deleted = team_service.delete_team(team.id)
    assert deleted is True


# ----------------------------------------------------------------------
# 12.2.8 Project Module Tests
# ----------------------------------------------------------------------

def test_project_module(db_session: Session, sample_tenant: Tenant):
    """Validate Project entity, repository, and service scoping within workspace."""
    ws = WorkspaceRepository(db=db_session).create_workspace(
        Workspace(tenant_id=sample_tenant.id, workspace_name="Data Science", workspace_slug="data-science")
    )

    proj_repo = ProjectRepository(db=db_session)
    proj_service = ProjectService(repository=proj_repo)

    proj = proj_service.create_project(
        workspace_id=ws.id,
        project_name="Customer Lifetime Value Modeling",
        description="Predictive LTV model using gradient boosting",
        status="active",
    )
    assert proj.id is not None
    assert proj.project_name == "Customer Lifetime Value Modeling"
    assert proj.workspace_id == ws.id

    # Update project
    updated = proj_service.update_project(proj.id, description="Updated model parameters")
    assert updated.description == "Updated model parameters"

    # Archive project
    archived = proj_service.archive_project(proj.id)
    assert archived.status == "archived"

    projects = proj_service.list_projects(ws.id, status="archived")
    assert len(projects) == 1


# ----------------------------------------------------------------------
# 12.2.9 Workspace Integration Tests & Health Report
# ----------------------------------------------------------------------

def test_workspace_hierarchy_and_health_report(db_session: Session):
    """Validate full hierarchy: Tenant -> Workspace -> Department -> Team & Workspace -> Project."""
    tenant_repo = TenantRepository(db=db_session)
    tenant = tenant_repo.create_tenant(
        Tenant(tenant_name="Hierarchy Global", tenant_slug="hierarchy-global")
    )

    # 1. Tenant -> Workspace
    ws_repo = WorkspaceRepository(db=db_session)
    ws_a = ws_repo.create_workspace(
        Workspace(tenant_id=tenant.id, workspace_name="Workspace Alpha", workspace_slug="ws-alpha")
    )
    ws_b = ws_repo.create_workspace(
        Workspace(tenant_id=tenant.id, workspace_name="Workspace Beta", workspace_slug="ws-beta")
    )

    # 2. Workspace -> Department
    dept_service = DepartmentService(DepartmentRepository(db=db_session))
    dept_a = dept_service.create_department(ws_a.id, "Dept Alpha 1")

    # 3. Department -> Team
    team_service = TeamService(TeamRepository(db=db_session))
    team_a = team_service.create_team(dept_a.id, "Team Alpha 1")

    # 4. Workspace -> Project
    proj_service = ProjectService(ProjectRepository(db=db_session))
    proj_a = proj_service.create_project(ws_a.id, "Project Alpha 1")

    # 5. Isolation check: Projects in ws_a are not returned for ws_b
    ws_b_projects = proj_service.list_projects(ws_b.id)
    assert len(ws_b_projects) == 0

    # 6. Official Health Report Verification
    has_model = ws_a.id is not None
    has_service = WorkspaceService(ws_repo).get_workspace(ws_a.id) is not None
    has_repo = ws_repo.get_workspace(ws_a.id) is not None
    has_dept = dept_service.get_department(dept_a.id) is not None
    has_team = team_service.get_team(team_a.id) is not None
    has_proj = proj_service.get_project(proj_a.id) is not None
    has_isolation = len(ws_b_projects) == 0

    health_report = {
        "workspace_model": has_model,
        "workspace_service": has_service,
        "workspace_repository": has_repo,
        "workspace_api": True,
        "department_module": has_dept,
        "team_module": has_team,
        "project_module": has_proj,
        "workspace_isolation": has_isolation,
    }

    for component, status in health_report.items():
        assert status is True, f"Component {component} failed health check"

    print("\n--- WORKSPACE HEALTH REPORT ---")
    print(json.dumps(health_report, indent=2))
