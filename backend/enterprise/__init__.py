"""Enterprise Expansion & Scale (Phase 12) Module."""

from backend.enterprise.agent_ecosystem import (
    AgentContribution,
    AgentDescriptor,
    AgentEcosystem,
    AgentRole,
    MissionStatus,
    MultiAgentMission,
)
from backend.enterprise.collaboration import (
    ActivityEvent,
    CollaborationManager,
    Comment,
    SharedTemplate,
    TeamBookmark,
)
from backend.enterprise.connectors import (
    AuthMethod,
    ConnectorCategory,
    ConnectorDefinition,
    ConnectorManager,
    InstalledConnector,
    SyncStatus,
)
from backend.enterprise.ecosystem_orchestrator import (
    EcosystemDirector,
    EnterpriseOnboardingResult,
)
from backend.enterprise.enterprise_integrations import (
    EnterpriseIntegrationHub,
    IntegrationChannel,
    WebhookEventType,
    WebhookSubscription,
)
from backend.enterprise.global_scale import (
    CloudRegion,
    ComplianceJurisdiction,
    GlobalScaleManager,
    RegionNode,
)
from backend.enterprise.mobile_platform import (
    CardType,
    ExecutiveMobileCard,
    MobilePlatform,
    MobilePlatformEngine,
)
from backend.enterprise.model_hub import (
    FineTunedAdapter,
    ModelHub,
    ModelInfo,
    ModelProvider,
    RoutingStrategy,
    TenantModelBudget,
)
from backend.enterprise.multi_tenant import (
    Tenant,
    TenantManager,
    TenantQuota,
    TenantStatus,
    TenantTier,
    TenantUsage,
    apply_tenant_filter,
    generate_rls_sql_policies,
    get_current_tenant_id,
    set_current_tenant_id,
    tenant_context,
    verify_tenant_access,
)
from backend.enterprise.workspace_manager import (
    Workspace,
    WorkspaceManager,
    WorkspaceMember,
    WorkspaceRole,
)

__all__ = [
    # 12.1 Multi-Tenant
    "Tenant",
    "TenantManager",
    "TenantQuota",
    "TenantStatus",
    "TenantTier",
    "TenantUsage",
    "apply_tenant_filter",
    "generate_rls_sql_policies",
    "get_current_tenant_id",
    "set_current_tenant_id",
    "tenant_context",
    "verify_tenant_access",
    # 12.2 Workspace
    "Workspace",
    "WorkspaceManager",
    "WorkspaceMember",
    "WorkspaceRole",
    # 12.3 Collaboration
    "ActivityEvent",
    "CollaborationManager",
    "Comment",
    "SharedTemplate",
    "TeamBookmark",
    # 12.4 Connectors
    "AuthMethod",
    "ConnectorCategory",
    "ConnectorDefinition",
    "ConnectorManager",
    "InstalledConnector",
    "SyncStatus",
    # 12.5 Agent Ecosystem
    "AgentContribution",
    "AgentDescriptor",
    "AgentEcosystem",
    "AgentRole",
    "MissionStatus",
    "MultiAgentMission",
    # 12.6 Model Hub
    "FineTunedAdapter",
    "ModelHub",
    "ModelInfo",
    "ModelProvider",
    "RoutingStrategy",
    "TenantModelBudget",
    # 12.7 Enterprise Integrations
    "EnterpriseIntegrationHub",
    "IntegrationChannel",
    "WebhookEventType",
    "WebhookSubscription",
    # 12.8 Mobile Platform
    "CardType",
    "ExecutiveMobileCard",
    "MobilePlatform",
    "MobilePlatformEngine",
    # 12.9 Global Scale
    "CloudRegion",
    "ComplianceJurisdiction",
    "GlobalScaleManager",
    "RegionNode",
    # 12.10 Ecosystem Orchestrator
    "EcosystemDirector",
    "EnterpriseOnboardingResult",
]
