"""
Phase 12.10.9 — Plugin Monitoring
Telemetry engine measuring third-party plugin execution frequencies,
error counts, p95 latencies, and resource consumption.
"""

from typing import Dict, Any, List, Optional
import time
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.plugins.monitoring")


class PluginExecutionMetric(BaseModel):
    plugin_id: str
    invocations: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    latencies: List[float] = Field(default_factory=list)
    memory_mb_samples: List[float] = Field(default_factory=list)

    @property
    def mean_latency_ms(self) -> float:
        return round(self.total_latency_ms / self.invocations, 2) if self.invocations else 0.0

    @property
    def error_rate(self) -> float:
        return round(self.errors / self.invocations, 4) if self.invocations else 0.0


class PluginMonitoringEngine:
    """
    Tracks runtime telemetry and performance budgets across all registered extensions.
    """

    def __init__(self):
        self._metrics: Dict[str, PluginExecutionMetric] = {}

    def record_invocation(
        self,
        plugin_id: str,
        latency_ms: float,
        is_error: bool = False,
        memory_mb: float = 12.0
    ):
        """Record execution metric for a plugin invocation."""
        rec = self._metrics.setdefault(plugin_id, PluginExecutionMetric(plugin_id=plugin_id))
        rec.invocations += 1
        rec.total_latency_ms += latency_ms
        rec.latencies.append(latency_ms)
        rec.memory_mb_samples.append(memory_mb)

        if is_error:
            rec.errors += 1
            logger.warning("Recorded execution error for plugin %s (total: %d)", plugin_id, rec.errors)

    def get_plugin_metrics(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve aggregated telemetry for a specific plugin."""
        rec = self._metrics.get(plugin_id)
        if not rec:
            return None
        return {
            "plugin_id": rec.plugin_id,
            "invocations": rec.invocations,
            "errors": rec.errors,
            "error_rate": rec.error_rate,
            "mean_latency_ms": rec.mean_latency_ms,
            "peak_memory_mb": max(rec.memory_mb_samples) if rec.memory_mb_samples else 0.0
        }

    def get_system_summary(self) -> Dict[str, Any]:
        """System-wide summary of plugin health."""
        total_invocations = sum(m.invocations for m in self._metrics.values())
        total_errors = sum(m.errors for m in self._metrics.values())
        return {
            "monitored_plugins": len(self._metrics),
            "total_invocations": total_invocations,
            "total_errors": total_errors,
            "system_health": "HEALTHY" if total_errors == 0 or (total_errors / max(1, total_invocations) < 0.05) else "DEGRADED"
        }
