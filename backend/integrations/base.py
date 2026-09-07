"""
Phase 12.7.2 — Enterprise Integration Framework
Abstract base class and core contracts for all enterprise integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.integrations.base")


class IntegrationHealthResult(BaseModel):
    """Health check outcome for an enterprise integration."""
    healthy: bool
    status_code: int = 200
    latency_ms: float = 0.0
    message: str = "Integration operational"
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = Field(default_factory=dict)


class IntegrationSyncResult(BaseModel):
    """Synchronization outcome for an enterprise integration."""
    success: bool
    records_synced: int = 0
    synced_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    errors: list[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseEnterpriseIntegration(ABC):
    """
    Abstract Base Class for all enterprise integrations.
    Supports OAuth, API Key, Webhook auth, sync, and health checks.
    """

    def __init__(self, integration_id: str, config: Optional[Dict[str, Any]] = None):
        self.integration_id = integration_id
        self.config = config or {}
        self.is_connected = False
        self._auth_type = self.config.get("auth_type", "api_key")  # oauth, api_key, webhook
        self.logger = logging.getLogger(f"backend.integrations.{self.__class__.__name__}")

    @property
    def auth_type(self) -> str:
        return self._auth_type

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection with the third-party enterprise platform."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Gracefully terminate connection / revoke session tokens."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate credentials, configuration parameters, and permissions."""
        pass

    @abstractmethod
    def health_check(self) -> IntegrationHealthResult:
        """Perform ping / health probe on the upstream integration."""
        pass

    @abstractmethod
    def sync(self, payload: Optional[Dict[str, Any]] = None) -> IntegrationSyncResult:
        """Synchronize data, bi-directionally or uni-directionally."""
        pass
