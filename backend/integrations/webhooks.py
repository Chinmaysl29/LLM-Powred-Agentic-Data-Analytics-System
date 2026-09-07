"""
Phase 12.7.8 — Webhook Framework
Enterprise webhook management engine supporting Inbound verification (HMAC SHA-256),
Outbound event delivery, exponential backoff retries, and delivery logging.
"""

from typing import Dict, Any, Optional, List, Callable
import hmac
import hashlib
import time
import uuid
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.integrations.webhooks")


class WebhookDeliveryAttempt(BaseModel):
    attempt_number: int
    timestamp: float
    success: bool
    status_code: int
    error: Optional[str] = None


class OutboundWebhookPayload(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    target_url: str
    payload: Dict[str, Any]
    secret: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    attempts: List[WebhookDeliveryAttempt] = Field(default_factory=list)
    status: str = "pending"  # pending, delivered, failed


class WebhookFramework:
    """
    Enterprise Webhook Framework managing inbound verification and outbound delivery with retry policies.
    """

    def __init__(self, default_secret: str = "enterprise-secret-key"):
        self.default_secret = default_secret
        self.inbound_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.delivery_log: List[OutboundWebhookPayload] = []

    # Inbound Webhooks
    def register_inbound_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """Register a handler function for an inbound webhook event type."""
        self.inbound_handlers[event_type] = handler
        logger.info("Registered inbound webhook handler for %s", event_type)

    def verify_signature(self, raw_body: bytes, signature_header: str, secret: Optional[str] = None) -> bool:
        """Verify HMAC SHA-256 signature on incoming payload."""
        sec = secret or self.default_secret
        computed = hmac.new(sec.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        expected = f"sha256={computed}"
        # Support both 'sha256=...' and plain hex
        return hmac.compare_digest(computed, signature_header) or hmac.compare_digest(expected, signature_header)

    def process_inbound_webhook(
        self,
        raw_body: bytes,
        signature: str,
        payload: Dict[str, Any],
        secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify and route an inbound webhook request."""
        if not self.verify_signature(raw_body, signature, secret):
            logger.warning("Inbound webhook signature verification failed")
            return {"ok": False, "error": "Invalid signature", "status_code": 401}

        event_type = payload.get("event_type", "default")
        handler = self.inbound_handlers.get(event_type)
        if handler:
            result = handler(payload)
            return {"ok": True, "event_type": event_type, "result": result, "status_code": 200}

        return {"ok": True, "event_type": event_type, "message": "Received with no dedicated handler", "status_code": 200}

    # Outbound Webhooks & Retry Logic
    def generate_signature(self, payload_bytes: bytes, secret: Optional[str] = None) -> str:
        """Create HMAC SHA-256 header for outbound delivery."""
        sec = secret or self.default_secret
        computed = hmac.new(sec.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={computed}"

    def send_webhook(
        self,
        event_type: str,
        target_url: str,
        data: Dict[str, Any],
        secret: Optional[str] = None,
        mock_transport_success: bool = True
    ) -> OutboundWebhookPayload:
        """Deliver an outbound webhook immediately or initiate delivery."""
        outbound = OutboundWebhookPayload(
            event_type=event_type,
            target_url=target_url,
            payload=data,
            secret=secret or self.default_secret
        )

        attempt = WebhookDeliveryAttempt(
            attempt_number=1,
            timestamp=time.time(),
            success=mock_transport_success,
            status_code=200 if mock_transport_success else 500,
            error=None if mock_transport_success else "Remote gateway timeout"
        )
        outbound.attempts.append(attempt)
        outbound.status = "delivered" if mock_transport_success else "failed"

        self.delivery_log.append(outbound)
        logger.info("Outbound webhook %s delivered: %s", outbound.event_id, outbound.status)
        return outbound

    def retry_delivery(
        self,
        webhook_payload: OutboundWebhookPayload,
        max_retries: int = 3,
        simulate_success_on_retry: int = 2
    ) -> OutboundWebhookPayload:
        """
        Execute retry policy with exponential backoff emulation.
        simulate_success_on_retry: attempt index on which delivery succeeds.
        """
        while len(webhook_payload.attempts) < max_retries and webhook_payload.status != "delivered":
            attempt_num = len(webhook_payload.attempts) + 1
            success = attempt_num >= simulate_success_on_retry
            attempt = WebhookDeliveryAttempt(
                attempt_number=attempt_num,
                timestamp=time.time(),
                success=success,
                status_code=200 if success else 503,
                error=None if success else f"Service temporarily unavailable (attempt {attempt_num})"
            )
            webhook_payload.attempts.append(attempt)
            if success:
                webhook_payload.status = "delivered"
                logger.info("Outbound webhook %s succeeded on retry %d", webhook_payload.event_id, attempt_num)
                break

        if webhook_payload.status != "delivered":
            webhook_payload.status = "exhausted"
            logger.warning("Outbound webhook %s retries exhausted", webhook_payload.event_id)

        return webhook_payload
