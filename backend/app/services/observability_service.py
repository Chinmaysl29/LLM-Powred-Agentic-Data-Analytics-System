"""Phase 22.1 — Enterprise Observability & Telemetry Layer.

Provides real-time metric counters, histograms, Prometheus exposition format,
and production-ready Grafana dashboard specifications for:
- Agent Latency & Request Counts
- Forecast Execution Duration & Errors
- RAG Document Retrieval & Token Counts
- SQL Generation Success & Guardrail Failures
- System Resource Telemetry (CPU & Memory)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List
import psutil

logger = logging.getLogger(__name__)


class ObservabilityService:
    """Enterprise metrics collector exporting Prometheus metrics and Grafana dashboards."""

    def __init__(self) -> None:
        self._counters: Dict[str, float] = {
            "ai_analyst_requests_total": 0.0,
            "ai_rag_retrievals_total": 0.0,
            "ai_sql_queries_total": 0.0,
            "ai_sql_errors_total": 0.0,
            "ai_forecast_runs_total": 0.0,
            "ai_forecast_errors_total": 0.0,
        }
        self._latencies: Dict[str, List[float]] = {
            "ai_analyst_duration_seconds": [],
            "ai_forecast_duration_seconds": [],
            "ai_sql_duration_seconds": [],
            "ai_rag_duration_seconds": [],
        }

    def record_request(self, metric_name: str, value: float = 1.0) -> None:
        """Increment a metric counter."""
        if metric_name in self._counters:
            self._counters[metric_name] += value
        else:
            self._counters[metric_name] = value

    def record_latency(self, metric_name: str, duration_sec: float) -> None:
        """Record execution duration in seconds."""
        if metric_name not in self._latencies:
            self._latencies[metric_name] = []
        self._latencies[metric_name].append(round(duration_sec, 4))
        # Keep recent 1000 observations
        if len(self._latencies[metric_name]) > 1000:
            self._latencies[metric_name] = self._latencies[metric_name][-1000:]

    def get_system_telemetry(self) -> Dict[str, Any]:
        """Collect host process CPU and memory utilization."""
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        return {
            "process_rss_bytes": mem_info.rss,
            "process_rss_mb": round(mem_info.rss / (1024 * 1024), 2),
            "process_vms_mb": round(mem_info.vms / (1024 * 1024), 2),
            "cpu_percent": process.cpu_percent(interval=None),
            "num_threads": process.num_threads(),
            "uptime_seconds": round(time.time() - process.create_time(), 2),
        }

    def generate_prometheus_metrics(self) -> str:
        """Format metrics in standard Prometheus exposition format."""
        telemetry = self.get_system_telemetry()
        lines = [
            "# HELP ai_analyst_requests_total Total number of autonomous analyst queries executed",
            "# TYPE ai_analyst_requests_total counter",
            f"ai_analyst_requests_total {self._counters.get('ai_analyst_requests_total', 0.0)}",
            "",
            "# HELP ai_rag_retrievals_total Total number of RAG knowledge retrieval passes",
            "# TYPE ai_rag_retrievals_total counter",
            f"ai_rag_retrievals_total {self._counters.get('ai_rag_retrievals_total', 0.0)}",
            "",
            "# HELP ai_sql_queries_total Total generated SQL statements executed",
            "# TYPE ai_sql_queries_total counter",
            f"ai_sql_queries_total {self._counters.get('ai_sql_queries_total', 0.0)}",
            "",
            "# HELP ai_sql_errors_total Total SQL guardrail and execution violations",
            "# TYPE ai_sql_errors_total counter",
            f"ai_sql_errors_total {self._counters.get('ai_sql_errors_total', 0.0)}",
            "",
            "# HELP ai_forecast_runs_total Total machine learning forecast runs executed",
            "# TYPE ai_forecast_runs_total counter",
            f"ai_forecast_runs_total {self._counters.get('ai_forecast_runs_total', 0.0)}",
            "",
            "# HELP process_memory_rss_bytes Process resident memory set in bytes",
            "# TYPE process_memory_rss_bytes gauge",
            f"process_memory_rss_bytes {telemetry['process_rss_bytes']}",
            "",
            "# HELP process_cpu_percent Process CPU utilization percent",
            "# TYPE process_cpu_percent gauge",
            f"process_cpu_percent {telemetry['cpu_percent']}",
        ]

        # Add latency summaries
        for metric, vals in self._latencies.items():
            if vals:
                p95 = float(np.percentile(vals, 95)) if len(vals) >= 2 else vals[0]
                avg = float(np.mean(vals))
                lines.extend([
                    f"# HELP {metric}_p95 95th percentile latency in seconds",
                    f"# TYPE {metric}_p95 gauge",
                    f"{metric}_p95 {round(p95, 4)}",
                    f"# HELP {metric}_avg Average latency in seconds",
                    f"# TYPE {metric}_avg gauge",
                    f"{metric}_avg {round(avg, 4)}",
                    "",
                ])

        return "\n".join(lines) + "\n"

    def generate_grafana_dashboard_json(self) -> Dict[str, Any]:
        """Generate a production-ready Grafana dashboard configuration."""
        return {
            "title": "AI Data Analyst OS — Enterprise Observability",
            "uid": "ai-data-analyst-os-main",
            "schemaVersion": 36,
            "version": 1,
            "refresh": "10s",
            "panels": [
                {
                    "title": "Autonomous Analyst Requests",
                    "type": "stat",
                    "gridPos": {"x": 0, "y": 0, "w": 6, "h": 4},
                    "targets": [{"expr": "ai_analyst_requests_total"}],
                },
                {
                    "title": "Forecast Execution Runs",
                    "type": "stat",
                    "gridPos": {"x": 6, "y": 0, "w": 6, "h": 4},
                    "targets": [{"expr": "ai_forecast_runs_total"}],
                },
                {
                    "title": "SQL Success Rate",
                    "type": "gauge",
                    "gridPos": {"x": 12, "y": 0, "w": 6, "h": 4},
                    "targets": [{"expr": "(ai_sql_queries_total - ai_sql_errors_total) / ai_sql_queries_total * 100"}],
                },
                {
                    "title": "Process Memory (MB)",
                    "type": "gauge",
                    "gridPos": {"x": 18, "y": 0, "w": 6, "h": 4},
                    "targets": [{"expr": "process_memory_rss_bytes / 1048576"}],
                },
                {
                    "title": "Agent Execution Latency (P95 vs Avg)",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 4, "w": 12, "h": 8},
                    "targets": [
                        {"expr": "ai_analyst_duration_seconds_p95", "legendFormat": "P95"},
                        {"expr": "ai_analyst_duration_seconds_avg", "legendFormat": "Avg"},
                    ],
                },
                {
                    "title": "Forecast Training Duration (sec)",
                    "type": "timeseries",
                    "gridPos": {"x": 12, "y": 4, "w": 12, "h": 8},
                    "targets": [
                        {"expr": "ai_forecast_duration_seconds_avg", "legendFormat": "Avg Training Time"},
                    ],
                },
            ],
        }


import numpy as np

_observability_service = ObservabilityService()


def get_observability_service() -> ObservabilityService:
    return _observability_service
