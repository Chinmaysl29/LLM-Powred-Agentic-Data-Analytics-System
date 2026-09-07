"""Phase 12.4.2 — Connector Framework.

Abstract connector interface and standardized lifecycle contracts for all
data connectors (Databases, Cloud Storage, CRMs, and Warehouses).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class ConnectorError(Exception):
    """Base exception for all connector operations."""
    pass


class ConnectorAuthError(ConnectorError):
    """Raised when authentication credentials fail."""
    pass


class ConnectorConnectionError(ConnectorError):
    """Raised when the target host cannot be reached."""
    pass


class ConnectorSyncError(ConnectorError):
    """Raised when synchronization encounters an unrecoverable failure."""
    pass


# ---------------------------------------------------------------------------
# Contract Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False


@dataclass
class TableInfo:
    table_name: str
    schema_name: str = "public"
    columns: List[ColumnInfo] = field(default_factory=list)
    estimated_rows: int = 0


@dataclass
class SchemaInfo:
    catalog_name: str
    tables: List[TableInfo] = field(default_factory=list)


@dataclass
class FileInfo:
    file_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    modified_at: datetime
    checksum: Optional[str] = None


@dataclass
class ValidationResult:
    is_valid: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    status: str  # "HEALTHY", "DEGRADED", "UNHEALTHY"
    latency_ms: float
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SyncResult:
    sync_id: str
    connector_id: str
    status: str  # "SUCCESS", "FAILED", "PARTIAL"
    rows_synced: int = 0
    bytes_synced: int = 0
    duration_ms: float = 0.0
    synced_resources: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Abstract Base Connector
# ---------------------------------------------------------------------------
class BaseConnector(ABC):
    """Abstract base class defining the standard interface for all data connectors."""

    def __init__(
        self,
        connector_id: str,
        name: str,
        config: Dict[str, Any],
    ) -> None:
        self.connector_id = connector_id
        self.name = name
        self.config = config
        self._is_connected = False
        self._last_health: Optional[HealthCheckResult] = None

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection or session to the external service."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Cleanly close connection and release resources."""
        pass

    @abstractmethod
    def validate(self) -> ValidationResult:
        """Verify credentials and configuration without performing ingestion."""
        pass

    @abstractmethod
    def sync(self, incremental: bool = False, **kwargs: Any) -> SyncResult:
        """Execute extraction and ingest records into the platform."""
        pass

    @abstractmethod
    def health_check(self) -> HealthCheckResult:
        """Ping external source and return connection latency and health status."""
        pass

    def mask_credentials(self) -> Dict[str, str]:
        """Return configuration with passwords, keys, and tokens redacted."""
        masked = {}
        sensitive_keys = {"password", "secret", "token", "api_key", "key", "private_key"}
        for k, v in self.config.items():
            str_v = str(v)
            if any(s in k.lower() for s in sensitive_keys):
                masked[k] = f"{str_v[:2]}...{str_v[-2:]}" if len(str_v) > 5 else "******"
            else:
                masked[k] = str_v
        return masked
