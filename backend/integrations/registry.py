"""
Phase 12.7.1 — Integration Registry
Tracks registered enterprise integrations, providers, configuration, and statuses.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.integrations.registry")


class IntegrationRecord(BaseModel):
    """Data representation of an enterprise integration registration."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    integration_name: str
    integration_type: str  # communication, project_management, productivity, erp, bi
    provider: str          # slack, teams, jira, google_workspace, office365, webhook
    status: str = "active" # active, disabled, pending_auth, error
    version: str = "1.0.0"
    config: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IntegrationRegistry:
    """
    Central registry managing enterprise integrations across tenants and providers.
    Supports in-memory caching and persistent store synchronization.
    """

    def __init__(self):
        self._integrations: Dict[str, IntegrationRecord] = {}

    def register_integration(
        self,
        integration_name: str,
        integration_type: str,
        provider: str,
        config: Optional[Dict[str, Any]] = None,
        version: str = "1.0.0",
        tenant_id: Optional[str] = None,
        status: str = "active"
    ) -> IntegrationRecord:
        """Register a new enterprise integration."""
        record = IntegrationRecord(
            integration_name=integration_name,
            integration_type=integration_type,
            provider=provider,
            config=config or {},
            version=version,
            tenant_id=tenant_id,
            status=status
        )
        self._integrations[record.id] = record
        logger.info("Registered integration %s (%s, provider: %s)", record.id, record.integration_name, record.provider)
        return record

    def get_integration(self, integration_id: str) -> Optional[IntegrationRecord]:
        """Retrieve an integration record by ID."""
        return self._integrations.get(integration_id)

    def update_integration(
        self,
        integration_id: str,
        config: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
        status: Optional[str] = None,
        integration_name: Optional[str] = None
    ) -> Optional[IntegrationRecord]:
        """Update integration configuration, version, or operational status."""
        record = self._integrations.get(integration_id)
        if not record:
            return None

        if config is not None:
            record.config.update(config)
        if version is not None:
            record.version = version
        if status is not None:
            record.status = status
        if integration_name is not None:
            record.integration_name = integration_name

        record.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info("Updated integration %s status: %s", integration_id, record.status)
        return record

    def disable_integration(self, integration_id: str) -> bool:
        """Deactivate an integration."""
        record = self._integrations.get(integration_id)
        if not record:
            return False
        record.status = "disabled"
        record.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info("Disabled integration %s", integration_id)
        return True

    def activate_integration(self, integration_id: str) -> bool:
        """Re-activate a disabled integration."""
        record = self._integrations.get(integration_id)
        if not record:
            return False
        record.status = "active"
        record.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info("Activated integration %s", integration_id)
        return True

    def list_integrations(
        self,
        tenant_id: Optional[str] = None,
        provider: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[IntegrationRecord]:
        """Query and filter registered integrations."""
        results = list(self._integrations.values())
        if tenant_id:
            results = [r for r in results if r.tenant_id == tenant_id]
        if provider:
            results = [r for r in results if r.provider == provider]
        if status:
            results = [r for r in results if r.status == status]
        return results

    def count(self) -> int:
        return len(self._integrations)
