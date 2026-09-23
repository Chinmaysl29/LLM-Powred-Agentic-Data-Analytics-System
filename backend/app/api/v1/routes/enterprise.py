"""REST API Endpoints for Enterprise Expansion & Scale (Phase 12)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.enterprise.agent_ecosystem import AgentEcosystem
from backend.enterprise.collaboration import CollaborationManager
from backend.enterprise.connectors import AuthMethod, ConnectorCategory, ConnectorManager
from backend.enterprise.ecosystem_orchestrator import EcosystemDirector
from backend.enterprise.enterprise_integrations import EnterpriseIntegrationHub, WebhookEventType
from backend.enterprise.global_scale import CloudRegion, GlobalScaleManager
from backend.enterprise.mobile_platform import MobilePlatformEngine
from backend.enterprise.model_hub import ModelHub, RoutingStrategy
from backend.enterprise.multi_tenant import TenantManager, TenantTier, get_current_tenant_id
from backend.enterprise.workspace_manager import WorkspaceManager, WorkspaceRole

router = APIRouter(prefix="/enterprise", tags=["Enterprise Expansion & Scale"])

tenant_mgr = TenantManager()
workspace_mgr = WorkspaceManager()
collab_mgr = CollaborationManager()
conn_mgr = ConnectorManager()
agent_eco = AgentEcosystem()
model_hub = ModelHub()
integration_hub = EnterpriseIntegrationHub()
mobile_engine = MobilePlatformEngine()
scale_mgr = GlobalScaleManager()
director = EcosystemDirector()


# ----------------------------------------------------------------------
# Request Schemas
# ----------------------------------------------------------------------

class CreateTenantRequest(BaseModel):
    name: str = Field(..., min_length=2)
    slug: Optional[str] = None
    tier: str = Field(default="professional")
    admin_email: str = Field(default="admin@tenant.internal")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateWorkspaceRequest(BaseModel):
    tenant_id: str
    name: str = Field(..., min_length=2)
    department: str = Field(default="Analytics")
    owner_id: str
    owner_email: str = "owner@tenant.internal"
    description: str = ""


class AddMemberRequest(BaseModel):
    user_id: str
    email: str
    role: str = "viewer"


class AddCommentRequest(BaseModel):
    tenant_id: str
    workspace_id: str
    target_type: str
    target_id: str
    author_id: str
    author_name: str
    content: str = Field(..., min_length=1)
    thread_id: Optional[str] = None


class CreateTemplateRequest(BaseModel):
    tenant_id: str
    workspace_id: str
    title: str = Field(..., min_length=2)
    sql_or_prompt: str = Field(..., min_length=2)
    author_id: str
    author_name: str
    tags: List[str] = Field(default_factory=list)
    description: str = ""


class InstallConnectorRequest(BaseModel):
    tenant_id: str
    connector_id: str
    instance_name: str
    auth_method: str = "basic_auth"
    credentials: Dict[str, Any] = Field(default_factory=dict)
    selected_tables: Optional[List[str]] = None


class SubmitMissionRequest(BaseModel):
    tenant_id: str
    workspace_id: str
    title: str = Field(..., min_length=2)
    goal: str = Field(..., min_length=5)
    dataset_id: Optional[str] = None


class RouteModelRequest(BaseModel):
    strategy: str = Field(default="cost_optimized")


class SetBudgetRequest(BaseModel):
    monthly_budget_usd: float = Field(..., gt=0)
    hard_limit: bool = True


class RegisterWebhookRequest(BaseModel):
    tenant_id: str
    target_url: str
    secret_key: str
    events: List[str] = Field(default_factory=lambda: ["dataset.uploaded", "anomaly.detected"])


class OnboardCustomerRequest(BaseModel):
    company_name: str = Field(..., min_length=2)
    admin_email: str
    slug: Optional[str] = None
    tier: str = "enterprise"
    region: str = "us-east-1"
    initial_connectors: Optional[List[str]] = None


# ----------------------------------------------------------------------
# 12.1 Multi-Tenant Architecture Endpoints
# ----------------------------------------------------------------------

@router.post("/tenants", status_code=status.HTTP_201_CREATED)
def create_tenant(payload: CreateTenantRequest) -> Dict[str, Any]:
    try:
        tier_enum = TenantTier(payload.tier.lower())
    except ValueError:
        tier_enum = TenantTier.PROFESSIONAL
    try:
        tenant = tenant_mgr.create_tenant(
            name=payload.name,
            slug=payload.slug,
            tier=tier_enum,
            admin_email=payload.admin_email,
            metadata=payload.metadata,
        )
        return tenant.to_dict()
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/tenants")
def list_tenants() -> List[Dict[str, Any]]:
    return [t.to_dict() for t in tenant_mgr.list_tenants()]


@router.get("/tenants/{tenant_id}")
def get_tenant(tenant_id: str) -> Dict[str, Any]:
    tenant = tenant_mgr.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant.to_dict()


@router.get("/tenants/{tenant_id}/stats")
def get_tenant_statistics(tenant_id: str) -> Dict[str, Any]:
    try:
        return tenant_mgr.get_tenant_stats(tenant_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")


# ----------------------------------------------------------------------
# 12.2 Workspace Management Endpoints
# ----------------------------------------------------------------------

@router.post("/workspaces", status_code=status.HTTP_201_CREATED)
def create_workspace(payload: CreateWorkspaceRequest) -> Dict[str, Any]:
    try:
        ws = workspace_mgr.create_workspace(
            tenant_id=payload.tenant_id,
            name=payload.name,
            department=payload.department,
            owner_id=payload.owner_id,
            owner_email=payload.owner_email,
            description=payload.description,
        )
        return ws.to_dict()
    except (KeyError, ValueError) as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/workspaces")
def list_workspaces(
    tenant_id: str = Query(...),
    department: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return [w.to_dict() for w in workspace_mgr.list_workspaces(tenant_id=tenant_id, department=department)]


@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: str) -> Dict[str, Any]:
    ws = workspace_mgr.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return ws.to_dict()


@router.post("/workspaces/{workspace_id}/members")
def add_workspace_member(workspace_id: str, payload: AddMemberRequest) -> Dict[str, Any]:
    try:
        role_enum = WorkspaceRole(payload.role.lower())
    except ValueError:
        role_enum = WorkspaceRole.VIEWER
    try:
        member = workspace_mgr.add_member(
            workspace_id=workspace_id,
            user_id=payload.user_id,
            email=payload.email,
            role=role_enum,
        )
        return member.to_dict()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")


# ----------------------------------------------------------------------
# 12.3 Team Collaboration Endpoints
# ----------------------------------------------------------------------

@router.post("/comments", status_code=status.HTTP_201_CREATED)
def add_comment(payload: AddCommentRequest) -> Dict[str, Any]:
    comment = collab_mgr.add_comment(
        tenant_id=payload.tenant_id,
        workspace_id=payload.workspace_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        author_id=payload.author_id,
        author_name=payload.author_name,
        content=payload.content,
        thread_id=payload.thread_id,
    )
    return comment.to_dict()


@router.get("/comments")
def list_comments(target_type: str = Query(...), target_id: str = Query(...)) -> List[Dict[str, Any]]:
    return [c.to_dict() for c in collab_mgr.list_comments(target_type, target_id)]


@router.post("/comments/threads/{thread_id}/resolve")
def resolve_thread(thread_id: str, user_id: str = Query(...)) -> Dict[str, Any]:
    count = collab_mgr.resolve_thread(thread_id, user_id)
    return {"thread_id": thread_id, "resolved_comments": count}


@router.post("/templates", status_code=status.HTTP_201_CREATED)
def create_template(payload: CreateTemplateRequest) -> Dict[str, Any]:
    tmpl = collab_mgr.create_template(
        tenant_id=payload.tenant_id,
        workspace_id=payload.workspace_id,
        title=payload.title,
        sql_or_prompt=payload.sql_or_prompt,
        author_id=payload.author_id,
        author_name=payload.author_name,
        tags=payload.tags,
        description=payload.description,
    )
    return tmpl.to_dict()


@router.get("/templates")
def list_templates(tenant_id: str = Query(...), tag: Optional[str] = None) -> List[Dict[str, Any]]:
    return [t.to_dict() for t in collab_mgr.list_templates(tenant_id=tenant_id, tag=tag)]


@router.get("/activity-feed")
def get_activity_feed(tenant_id: str = Query(...), limit: int = 50) -> List[Dict[str, Any]]:
    return [a.to_dict() for a in collab_mgr.get_activity_feed(tenant_id=tenant_id, limit=limit)]


# ----------------------------------------------------------------------
# 12.4 Connector Marketplace Endpoints
# ----------------------------------------------------------------------

@router.get("/connectors/catalog")
def get_connector_catalog(category: Optional[str] = None) -> List[Dict[str, Any]]:
    cat_enum = None
    if category:
        try:
            cat_enum = ConnectorCategory(category.lower())
        except ValueError:
            pass
    return [c.to_dict() for c in conn_mgr.get_catalog(cat_enum)]


@router.post("/connectors/install", status_code=status.HTTP_201_CREATED)
def install_connector(payload: InstallConnectorRequest) -> Dict[str, Any]:
    try:
        auth_enum = AuthMethod(payload.auth_method.lower())
    except ValueError:
        auth_enum = AuthMethod.BASIC_AUTH
    try:
        inst = conn_mgr.install_connector(
            tenant_id=payload.tenant_id,
            connector_id=payload.connector_id,
            instance_name=payload.instance_name,
            auth_method=auth_enum,
            credentials=payload.credentials,
            selected_tables=payload.selected_tables,
        )
        return inst.to_dict()
    except (KeyError, ValueError) as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/connectors/{installed_id}/test")
def test_connector(installed_id: str) -> Dict[str, Any]:
    try:
        return conn_mgr.test_connection(installed_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")


@router.post("/connectors/{installed_id}/sync")
def sync_connector(installed_id: str, table_name: Optional[str] = None) -> Dict[str, Any]:
    try:
        return conn_mgr.sync_data(installed_id, table_name)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")


@router.get("/connectors/installed")
def list_installed_connectors(tenant_id: str = Query(...)) -> List[Dict[str, Any]]:
    return [c.to_dict() for c in conn_mgr.list_installed(tenant_id)]


# ----------------------------------------------------------------------
# 12.5 Advanced Agent Ecosystem Endpoints
# ----------------------------------------------------------------------

@router.get("/agents")
def get_agents() -> List[Dict[str, Any]]:
    return [a.to_dict() for a in agent_eco.get_registered_agents()]


@router.post("/missions", status_code=status.HTTP_201_CREATED)
def submit_mission(payload: SubmitMissionRequest) -> Dict[str, Any]:
    mission = agent_eco.submit_mission(
        tenant_id=payload.tenant_id,
        workspace_id=payload.workspace_id,
        title=payload.title,
        goal=payload.goal,
        dataset_id=payload.dataset_id,
    )
    return mission.to_dict()


@router.post("/missions/{mission_id}/execute")
def execute_mission(mission_id: str) -> Dict[str, Any]:
    try:
        completed = agent_eco.execute_mission(mission_id)
        return completed.to_dict()
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")


@router.get("/missions/{mission_id}")
def get_mission(mission_id: str) -> Dict[str, Any]:
    mission = agent_eco.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")
    return mission.to_dict()


# ----------------------------------------------------------------------
# 12.6 AI Model Hub Endpoints
# ----------------------------------------------------------------------

@router.get("/models")
def get_model_catalog() -> List[Dict[str, Any]]:
    return [m.to_dict() for m in model_hub.get_catalog()]


@router.post("/models/route")
def route_model(payload: RouteModelRequest) -> Dict[str, Any]:
    try:
        strat_enum = RoutingStrategy(payload.strategy.lower())
    except ValueError:
        strat_enum = RoutingStrategy.COST_OPTIMIZED
    model = model_hub.route_request(strat_enum)
    return {"selected_model": model.to_dict(), "strategy_applied": strat_enum.value}


@router.get("/models/budget/{tenant_id}")
def get_model_budget(tenant_id: str) -> Dict[str, Any]:
    return model_hub.get_budget(tenant_id).to_dict()


@router.post("/models/budget/{tenant_id}")
def set_model_budget(tenant_id: str, payload: SetBudgetRequest) -> Dict[str, Any]:
    b = model_hub.set_budget(tenant_id, payload.monthly_budget_usd, payload.hard_limit)
    return b.to_dict()


# ----------------------------------------------------------------------
# 12.7 Enterprise Integrations Endpoints
# ----------------------------------------------------------------------

@router.post("/integrations/webhooks", status_code=status.HTTP_201_CREATED)
def register_webhook(payload: RegisterWebhookRequest) -> Dict[str, Any]:
    event_enums = []
    for e in payload.events:
        try:
            event_enums.append(WebhookEventType(e))
        except ValueError:
            pass
    sub = integration_hub.register_webhook(
        tenant_id=payload.tenant_id,
        target_url=payload.target_url,
        secret_key=payload.secret_key,
        events=event_enums,
    )
    return sub.to_dict()


@router.post("/integrations/slack/preview")
def preview_slack_alert(title: str, message: str, severity: str = "INFO") -> Dict[str, Any]:
    return integration_hub.format_slack_alert(title, message, severity)


# ----------------------------------------------------------------------
# 12.8 Mobile Platform Endpoints
# ----------------------------------------------------------------------

@router.get("/mobile/feed")
def get_mobile_executive_feed(
    tenant_id: str = Query(default="system"),
    user_id: str = Query(default="usr-executive"),
) -> List[Dict[str, Any]]:
    return [c.to_dict() for c in mobile_engine.get_executive_feed(tenant_id, user_id)]


@router.get("/mobile/offline-manifest")
def get_offline_manifest(
    tenant_id: str = Query(default="system"),
    workspace_id: str = Query(default="ws-default"),
) -> Dict[str, Any]:
    return mobile_engine.generate_offline_manifest(tenant_id, workspace_id)


# ----------------------------------------------------------------------
# 12.9 Global Scale Endpoints
# ----------------------------------------------------------------------

@router.get("/global/topology")
def get_global_topology() -> List[Dict[str, Any]]:
    return [r.to_dict() for r in scale_mgr.get_topology()]


@router.post("/global/route")
def route_regional_query(
    tenant_id: str = Query(...),
    operation: str = Query(default="read"),
    client_country: Optional[str] = None,
) -> Dict[str, Any]:
    return scale_mgr.route_request(tenant_id, operation, client_country)


# ----------------------------------------------------------------------
# 12.10 Ecosystem Director Endpoints
# ----------------------------------------------------------------------

@router.get("/ecosystem/status")
def get_ecosystem_status() -> Dict[str, Any]:
    return director.get_ecosystem_overview()


@router.post("/ecosystem/onboard", status_code=status.HTTP_201_CREATED)
def onboard_enterprise_customer(payload: OnboardCustomerRequest) -> Dict[str, Any]:
    try:
        tier_enum = TenantTier(payload.tier.lower())
    except ValueError:
        tier_enum = TenantTier.ENTERPRISE
    try:
        region_enum = CloudRegion(payload.region.lower())
    except ValueError:
        region_enum = CloudRegion.US_EAST

    result = director.onboard_enterprise_customer(
        company_name=payload.company_name,
        admin_email=payload.admin_email,
        slug=payload.slug,
        tier=tier_enum,
        region=region_enum,
        initial_connectors=payload.initial_connectors,
    )
    return result.to_dict()


@router.get("/ecosystem/readiness")
def get_enterprise_readiness_scorecard() -> Dict[str, Any]:
    return director.evaluate_enterprise_readiness_scorecard()
