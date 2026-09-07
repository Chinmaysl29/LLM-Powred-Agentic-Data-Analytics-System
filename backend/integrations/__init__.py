"""
Phase 12.7 — Enterprise Integrations Platform Package Exports
"""

from backend.integrations.base import (
    BaseEnterpriseIntegration,
    IntegrationHealthResult,
    IntegrationSyncResult,
)
from backend.integrations.registry import (
    IntegrationRegistry,
    IntegrationRecord,
)
from backend.integrations.slack import SlackIntegration
from backend.integrations.teams import TeamsIntegration
from backend.integrations.jira import JiraIntegration
from backend.integrations.google_workspace import GoogleWorkspaceIntegration
from backend.integrations.office365 import Office365Integration
from backend.integrations.webhooks import (
    WebhookFramework,
    OutboundWebhookPayload,
    WebhookDeliveryAttempt,
)
from backend.integrations.events import (
    EventProcessingEngine,
    EnterpriseEvent,
    EventAuditLog,
)

__all__ = [
    "BaseEnterpriseIntegration",
    "IntegrationHealthResult",
    "IntegrationSyncResult",
    "IntegrationRegistry",
    "IntegrationRecord",
    "SlackIntegration",
    "TeamsIntegration",
    "JiraIntegration",
    "GoogleWorkspaceIntegration",
    "Office365Integration",
    "WebhookFramework",
    "OutboundWebhookPayload",
    "WebhookDeliveryAttempt",
    "EventProcessingEngine",
    "EnterpriseEvent",
    "EventAuditLog",
]
