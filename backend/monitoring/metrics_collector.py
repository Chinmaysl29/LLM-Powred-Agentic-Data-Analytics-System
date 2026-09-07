"""Monitoring & Observability Engine for Phase 8.

Tracks:
- Request Latency
- Forecast Runtime
- LLM Token Usage
- Database Query Time
- System Health

Output schema:
{
  "service": "forecasting",
  "latency": 240,
  "status": "healthy"
}
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

logger = logging.getLogger("monitoring")


class MetricsCollector:
    """Enterprise metrics, latency profiling, and service health observer."""

    def __init__(self) -> None:
        self._metrics: list[dict[str, Any]] = []
        self._service_health: dict[str, dict[str, Any]] = {
            "api_gateway": {"latency": 45, "status": "healthy", "last_check": datetime.now(timezone.utc).isoformat()},
            "database": {"latency": 12, "status": "healthy", "last_check": datetime.now(timezone.utc).isoformat()},
            "forecasting": {"latency": 240, "status": "healthy", "last_check": datetime.now(timezone.utc).isoformat()},
            "recommendations": {"latency": 180, "status": "healthy", "last_check": datetime.now(timezone.utc).isoformat()},
            "rag": {"latency": 150, "status": "healthy", "last_check": datetime.now(timezone.utc).isoformat()},
            "llm": {"latency": 620, "status": "healthy", "last_check": datetime.now(timezone.utc).isoformat()},
        }
        self._token_usage: list[dict[str, Any]] = []

    def record_service_health(
        self,
        service: str,
        latency: float,
        status: str = "healthy",
        error: str | None = None,
    ) -> dict[str, Any]:
        """Record health check and latency for a given service."""
        clean_status = status.lower()
        record: dict[str, Any] = {
            "service": service,
            "latency": round(float(latency), 2),
            "status": clean_status,
        }
        if error:
            record["error"] = error

        self._service_health[service] = {
            "latency": record["latency"],
            "status": record["status"],
            "error": error,
            "last_check": datetime.now(timezone.utc).isoformat(),
        }

        self._metrics.append({
            "service": service,
            "metric": "health_check",
            "latency_ms": record["latency"],
            "status": record["status"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return record

    def record_metric(
        self,
        service: str,
        metric_name: str,
        value: float,
        unit: str = "ms",
        tags: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an arbitrary telemetry metric."""
        entry = {
            "service": service,
            "metric": metric_name,
            "value": round(value, 3),
            "unit": unit,
            "tags": tags or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._metrics.append(entry)
        return entry

    def record_token_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4o",
        agent: str = "general",
    ) -> dict[str, Any]:
        """Record LLM token consumption metrics."""
        total = prompt_tokens + completion_tokens
        entry = {
            "agent": agent,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._token_usage.append(entry)
        self.record_metric("llm", "token_usage", total, unit="tokens", tags={"model": model, "agent": agent})
        return entry

    @contextmanager
    def track_time(self, service: str, operation: str) -> Generator[None, None, None]:
        """Context manager to measure runtime latency."""
        start = time.perf_counter()
        failed = False
        err_msg = None
        try:
            yield
        except Exception as exc:
            failed = True
            err_msg = str(exc)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            status = "unhealthy" if failed else "healthy"
            self.record_service_health(service, elapsed_ms, status=status, error=err_msg)
            self.record_metric(service, f"{operation}_latency", elapsed_ms, unit="ms")

    def detect_anomalies(
        self,
        service: str | None = None,
        latency_spike_threshold_ms: float = 1000.0,
    ) -> list[dict[str, Any]]:
        """Detect latency spikes or failure events across recorded metrics."""
        anomalies: list[dict[str, Any]] = []

        # Check recorded metrics
        candidates = self._metrics
        if service:
            candidates = [m for m in candidates if m.get("service") == service]

        for m in candidates:
            lat = m.get("latency_ms") or (m.get("value") if m.get("unit") == "ms" else 0)
            if lat and lat > latency_spike_threshold_ms:
                anomalies.append({
                    "type": "latency_spike",
                    "service": m.get("service"),
                    "latency": lat,
                    "threshold": latency_spike_threshold_ms,
                    "timestamp": m.get("timestamp"),
                })
            if m.get("status") in {"unhealthy", "failed", "degraded"}:
                anomalies.append({
                    "type": "service_failure",
                    "service": m.get("service"),
                    "details": m,
                    "timestamp": m.get("timestamp"),
                })

        return anomalies

    def get_system_health(self) -> dict[str, Any]:
        """Aggregate system-wide health status."""
        services = self._service_health
        statuses = [s["status"] for s in services.values()]

        if any(st == "unhealthy" for st in statuses):
            overall = "degraded"
        elif any(st == "degraded" for st in statuses):
            overall = "degraded"
        else:
            overall = "healthy"

        avg_latency = (
            sum(s["latency"] for s in services.values()) / len(services)
            if services
            else 0.0
        )

        return {
            "status": overall,
            "average_latency_ms": round(avg_latency, 2),
            "services": services,
            "total_tokens_consumed": sum(t["total_tokens"] for t in self._token_usage),
            "metrics_count": len(self._metrics),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def clear(self) -> None:
        """Reset metrics for test isolation."""
        self._metrics.clear()
        self._token_usage.clear()


# Global metrics collector singleton
metrics_collector = MetricsCollector()
