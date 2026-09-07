"""Structured enterprise audit logger for Phase 8.

Tracks:
- User Login
- Dataset Upload
- Forecast Run
- SQL Query Execution
- Recommendation Generation
- Report Download

Outputs standard event format:
{
  "event": "forecast_executed",
  "user": "analyst@company.com",
  "timestamp": "2026-03-09T10:00:00"
}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.core.config import get_settings

logger = logging.getLogger("audit")


class AuditLogger:
    """Enterprise audit logger maintaining structured event records."""

    def __init__(self, in_memory_capacity: int = 1000) -> None:
        try:
            self._enabled = get_settings().enable_audit_logs
        except Exception:
            self._enabled = True
        self._history: list[dict[str, Any]] = []
        self._capacity = in_memory_capacity

    def record_event(
        self,
        event: str,
        user: str,
        details: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Record an audit event and return standard audit dictionary."""
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        record: dict[str, Any] = {
            "event": event,
            "user": user,
            "timestamp": ts,
        }
        if details:
            record["details"] = details

        # Buffer history
        self._history.append(record)
        if len(self._history) > self._capacity:
            self._history.pop(0)

        # Log out
        if self._enabled:
            logger.info("AUDIT %s", json.dumps(record, default=str))

        return record

    def log_login(self, user: str, ip: str | None = None, success: bool = True) -> dict[str, Any]:
        """Record user login action."""
        event = "user_login" if success else "user_login_failed"
        return self.record_event(
            event=event,
            user=user,
            details={"ip_address": ip, "status": "success" if success else "failed"},
        )

    def log_dataset_upload(
        self, user: str, dataset_id: str, filename: str, row_count: int | None = None
    ) -> dict[str, Any]:
        """Record dataset upload event."""
        return self.record_event(
            event="dataset_upload",
            user=user,
            details={"dataset_id": dataset_id, "filename": filename, "row_count": row_count},
        )

    def log_forecast_run(
        self,
        user: str,
        target_column: str,
        model_type: str = "auto",
        horizon: int = 30,
    ) -> dict[str, Any]:
        """Record forecast execution event."""
        return self.record_event(
            event="forecast_executed",
            user=user,
            details={"target_column": target_column, "model_type": model_type, "horizon": horizon},
        )

    def log_sql_execution(
        self, user: str, query: str, execution_time_ms: float | None = None
    ) -> dict[str, Any]:
        """Record SQL query execution event."""
        return self.record_event(
            event="sql_query_executed",
            user=user,
            details={"query": query[:300], "execution_time_ms": execution_time_ms},
        )

    def log_recommendation_generation(
        self, user: str, domain: str = "business", count: int = 1
    ) -> dict[str, Any]:
        """Record recommendation generation event."""
        return self.record_event(
            event="recommendation_generated",
            user=user,
            details={"domain": domain, "count": count},
        )

    def log_report_download(
        self, user: str, report_id: str, format_type: str = "pdf"
    ) -> dict[str, Any]:
        """Record report download event."""
        return self.record_event(
            event="report_downloaded",
            user=user,
            details={"report_id": report_id, "format": format_type},
        )

    def get_audit_records(
        self,
        user: str | None = None,
        event: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query in-memory audit trail filtered by user or event type."""
        records = self._history
        if user:
            records = [r for r in records if r.get("user") == user]
        if event:
            records = [r for r in records if r.get("event") == event]
        return records[-limit:]

    def clear_history(self) -> None:
        """Clear audit history (for test isolation)."""
        self._history.clear()


# Global audit logger singleton
audit_logger = AuditLogger()
