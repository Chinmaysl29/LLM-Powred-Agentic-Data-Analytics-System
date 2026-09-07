"""
Phase 12.10 — Plugin & Extension Ecosystem Package Exports
"""

from backend.plugins.framework import (
    PluginFramework,
    PluginMetadata,
    PluginState,
)
from backend.plugins.registry import (
    PluginRegistry,
    PluginRecord,
)
from backend.plugins.agent_sdk import (
    BaseAgentPlugin,
    AgentPluginResult,
)
from backend.plugins.connector_sdk import (
    BaseConnectorPlugin,
    ConnectorQueryResult,
)
from backend.plugins.workflow_sdk import (
    BaseWorkflowPlugin,
    WorkflowExecutionResult,
)
from backend.plugins.dashboard_sdk import (
    BaseDashboardWidgetPlugin,
    DashboardWidgetRender,
)
from backend.plugins.marketplace import (
    MarketplaceEngine,
    MarketplaceItem,
)
from backend.plugins.sandbox import (
    PluginSandbox,
    SandboxPermissions,
)
from backend.plugins.monitoring import (
    PluginMonitoringEngine,
    PluginExecutionMetric,
)

__all__ = [
    "PluginFramework",
    "PluginMetadata",
    "PluginState",
    "PluginRegistry",
    "PluginRecord",
    "BaseAgentPlugin",
    "AgentPluginResult",
    "BaseConnectorPlugin",
    "ConnectorQueryResult",
    "BaseWorkflowPlugin",
    "WorkflowExecutionResult",
    "BaseDashboardWidgetPlugin",
    "DashboardWidgetRender",
    "MarketplaceEngine",
    "MarketplaceItem",
    "PluginSandbox",
    "SandboxPermissions",
    "PluginMonitoringEngine",
    "PluginExecutionMetric",
]
