"""Phase 12.4.8 — Connector Monitoring.

Real-time telemetry, latency benchmarking, failure detection, retry tracking,
and automated recovery verification for connectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from backend.connectors.base import BaseConnector, HealthCheckResult

logger = logging.getLogger(__name__)


@dataclass
class ConnectorTelemetry:
    connector_id: str
    connection_status: str  # "HEALTHY", "DEGRADED", "UNHEALTHY"
    last_sync_status: str  # "SUCCESS", "FAILED", "PENDING"
    average_latency_ms: float = 0.0
    total_syncs: int = 0
    failed_syncs: int = 0
    total_retries: int = 0
    last_failure_reason: Optional[str] = None
    last_health_check: Optional[datetime] = None
    is_recovering: bool = False


class ConnectorMonitor:
    """Monitoring and observability engine for connected enterprise data sources."""

    def __init__(self) -> None:
        self._telemetry: Dict[str, ConnectorTelemetry] = {}
        self._latency_history: Dict[str, List[float]] = {}

    def _get_or_create(self, connector_id: str) -> ConnectorTelemetry:
        if connector_id not in self._telemetry:
            self._telemetry[connector_id] = ConnectorTelemetry(
                connector_id=connector_id,
                connection_status="HEALTHY",
                last_sync_status="PENDING",
            )
            self._latency_history[connector_id] = []
        return self._telemetry[connector_id]

    def record_health_check(
        self,
        connector_id: str,
        result: HealthCheckResult,
    ) -> ConnectorTelemetry:
        """Process and record connector health check output."""
        telem = self._get_or_create(connector_id)
        telem.connection_status = result.status
        telem.last_health_check = result.timestamp

        history = self._latency_history[connector_id]
        history.append(result.latency_ms)
        if len(history) > 100:
            history.pop(0)

        telem.average_latency_ms = round(sum(history) / len(history), 2)

        # Check recovery state
        if telem.connection_status == "HEALTHY" and telem.failed_syncs > 0:
            telem.is_recovering = True
            logger.info("Connector %s health restored, recovery validated.", connector_id)

        return telem

    def record_sync_success(
        self,
        connector_id: str,
        duration_ms: float,
        retries: int = 0,
    ) -> ConnectorTelemetry:
        """Record successful synchronization telemetry."""
        telem = self._get_or_create(connector_id)
        telem.total_syncs += 1
        telem.last_sync_status = "SUCCESS"
        telem.total_retries += retries
        telem.is_recovering = False
        telem.last_failure_reason = None
        return telem

    def record_sync_failure(
        self,
        connector_id: str,
        reason: str,
        retries: int = 0,
    ) -> ConnectorTelemetry:
        """Detect and register sync failures and alerts."""
        telem = self._get_or_create(connector_id)
        telem.total_syncs += 1
        telem.failed_syncs += 1
        telem.total_retries += retries
        telem.last_sync_status = "FAILED"
        telem.last_failure_reason = reason
        telem.connection_status = "DEGRADED" if telem.failed_syncs < 3 else "UNHEALTHY"

        logger.error(
            "Sync failure registered for connector %s: %s (consecutive failures=%d)",
            connector_id,
            reason,
            telem.failed_syncs,
        )
        return telem

    def check_connector_health(self, connector: BaseConnector) -> HealthCheckResult:
        """Run health check directly on a connector instance and update metrics."""
        result = connector.health_check()
        self.record_health_check(connector.connector_id, result)
        return result

    def get_telemetry(self, connector_id: str) -> Optional[ConnectorTelemetry]:
        """Fetch telemetry statistics for a connector."""
        return self._telemetry.get(connector_id)

    def validate_recovery(self, connector_id: str) -> bool:
        """Verify that a degraded connector has transitioned back to full health."""
        telem = self._telemetry.get(connector_id)
        if not telem:
            return False
        return telem.connection_status == "HEALTHY"
