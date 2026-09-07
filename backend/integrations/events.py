"""
Phase 12.7.9 — Event Processing Engine
Enterprise asynchronous event engine supporting in-memory queuing, topic routing,
retry policies, Dead Letter Queue (DLQ), and immutable audit logs.
"""

from typing import Dict, Any, Optional, List, Callable
import time
import uuid
import logging
from collections import deque
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.integrations.events")


class EnterpriseEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    payload: Dict[str, Any]
    tenant_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    status: str = "queued" # queued, processing, completed, failed, dlq
    error_reason: Optional[str] = None


class EventAuditLog(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str
    topic: str
    action: str
    timestamp: float = Field(default_factory=time.time)
    details: Dict[str, Any] = Field(default_factory=dict)


class EventProcessingEngine:
    """
    Core event processing pipeline for enterprise platform operations.
    Handles queueing, subscribers, retries, DLQ, and audit tracking.
    """

    def __init__(self):
        self._queue: deque[EnterpriseEvent] = deque()
        self._subscribers: Dict[str, List[Callable[[EnterpriseEvent], bool]]] = {}
        self._dlq: List[EnterpriseEvent] = []
        self._audit_logs: List[EventAuditLog] = []

    def subscribe(self, topic: str, handler: Callable[[EnterpriseEvent], bool]):
        """Subscribe a handler callback to a specific event topic or wildcard '*'."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)
        logger.info("Subscribed handler to topic '%s'", topic)

    def publish(self, topic: str, payload: Dict[str, Any], tenant_id: Optional[str] = None, max_retries: int = 3) -> EnterpriseEvent:
        """Enqueue a new event into the processing pipeline."""
        event = EnterpriseEvent(
            topic=topic,
            payload=payload,
            tenant_id=tenant_id,
            max_retries=max_retries,
            status="queued"
        )
        self._queue.append(event)
        self._log_audit(event.id, topic, "PUBLISHED", {"tenant_id": tenant_id})
        logger.info("Published event %s on topic '%s'", event.id, topic)
        return event

    def process_next(self, simulate_handler_failure: bool = False) -> Optional[EnterpriseEvent]:
        """Dequeues and routes the next available event to subscribed handlers."""
        if not self._queue:
            return None

        event = self._queue.popleft()
        event.status = "processing"
        self._log_audit(event.id, event.topic, "PROCESSING_STARTED")

        handlers = self._subscribers.get(event.topic, []) + self._subscribers.get("*", [])

        if not handlers:
            # No handlers registered: complete by default
            event.status = "completed"
            self._log_audit(event.id, event.topic, "COMPLETED_NO_HANDLERS")
            return event

        success = True
        error_msg = None

        if simulate_handler_failure:
            success = False
            error_msg = "Simulated consumer processing failure"
        else:
            for handler in handlers:
                try:
                    res = handler(event)
                    if res is False:
                        success = False
                        error_msg = "Handler returned failure status"
                        break
                except Exception as ex:
                    success = False
                    error_msg = str(ex)
                    break

        if success:
            event.status = "completed"
            self._log_audit(event.id, event.topic, "COMPLETED_SUCCESSFULLY")
            logger.info("Event %s completed successfully", event.id)
            return event
        else:
            return self._handle_failure(event, error_msg or "Unknown processing error")

    def _handle_failure(self, event: EnterpriseEvent, error_reason: str) -> EnterpriseEvent:
        """Apply retry logic or route to Dead Letter Queue if retries exhausted."""
        event.retry_count += 1
        event.error_reason = error_reason

        if event.retry_count <= event.max_retries:
            event.status = "queued"
            self._queue.append(event)
            self._log_audit(event.id, event.topic, "RETRY_SCHEDULED", {
                "retry_count": event.retry_count,
                "max_retries": event.max_retries,
                "error": error_reason
            })
            logger.warning("Event %s failed (attempt %d/%d), re-queued", event.id, event.retry_count, event.max_retries)
        else:
            event.status = "dlq"
            self._dlq.append(event)
            self._log_audit(event.id, event.topic, "MOVED_TO_DLQ", {
                "final_error": error_reason,
                "retries": event.retry_count
            })
            logger.error("Event %s exhausted retries, routed to Dead Letter Queue (DLQ)", event.id)

        return event

    def retry_dlq_event(self, event_id: str) -> Optional[EnterpriseEvent]:
        """Re-queue an event from the Dead Letter Queue."""
        for idx, ev in enumerate(self._dlq):
            if ev.id == event_id:
                del self._dlq[idx]
                ev.status = "queued"
                ev.retry_count = 0
                self._queue.append(ev)
                self._log_audit(ev.id, ev.topic, "REPLAYED_FROM_DLQ")
                logger.info("Replayed DLQ event %s back to queue", event_id)
                return ev
        return None

    def get_dlq_events(self) -> List[EnterpriseEvent]:
        """Retrieve all dead-lettered events."""
        return list(self._dlq)

    def get_audit_logs(self, event_id: Optional[str] = None) -> List[EventAuditLog]:
        """Fetch audit log history."""
        if event_id:
            return [l for l in self._audit_logs if l.event_id == event_id]
        return list(self._audit_logs)

    def queue_size(self) -> int:
        return len(self._queue)

    def dlq_size(self) -> int:
        return len(self._dlq)

    def _log_audit(self, event_id: str, topic: str, action: str, details: Optional[Dict[str, Any]] = None):
        self._audit_logs.append(
            EventAuditLog(
                event_id=event_id,
                topic=topic,
                action=action,
                details=details or {}
            )
        )
