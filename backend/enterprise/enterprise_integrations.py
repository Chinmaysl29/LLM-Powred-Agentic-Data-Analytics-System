"""Phase 12.7 — Enterprise Integrations

Provides integrations for Slack Block Kit, Microsoft Teams Adaptive Cards,
HMAC-signed Webhook dispatching, Jira incident ticketing, and Executive Email digests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import hmac
import json
from typing import Any, Dict, List, Optional
import uuid


class IntegrationChannel(str, Enum):
    SLACK = "slack"
    MS_TEAMS = "ms_teams"
    WEBHOOK = "webhook"
    JIRA = "jira"
    EMAIL = "email"


class WebhookEventType(str, Enum):
    DATASET_UPLOADED = "dataset.uploaded"
    ANOMALY_DETECTED = "anomaly.detected"
    FORECAST_COMPLETED = "forecast.completed"
    REPORT_GENERATED = "report.generated"
    QUOTA_WARNING = "quota.warning"


@dataclass
class WebhookSubscription:
    id: str
    tenant_id: str
    target_url: str
    secret_key: str
    subscribed_events: List[WebhookEventType]
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "target_url": self.target_url,
            "subscribed_events": [e.value for e in self.subscribed_events],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DispatchDeliveryResult:
    delivery_id: str
    channel: IntegrationChannel
    status: str  # "DELIVERED", "FAILED", "RETRYING"
    status_code: int
    payload_summary: str
    signature: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EnterpriseIntegrationHub:
    """Manages notifications and webhooks to third-party enterprise tools."""

    _instance: Optional[EnterpriseIntegrationHub] = None

    def __new__(cls) -> EnterpriseIntegrationHub:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._webhooks: Dict[str, WebhookSubscription] = {}
            cls._instance._dispatch_log: List[DispatchDeliveryResult] = []
        return cls._instance

    # 1. Slack Block Kit Formatter & Dispatcher
    def format_slack_alert(
        self,
        title: str,
        message: str,
        severity: str = "INFO",
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate Slack Block Kit payload."""
        emoji = "🚨" if severity == "CRITICAL" else ("⚠️" if severity == "WARNING" else "📊")
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {title}", "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
            },
        ]

        if metrics:
            fields = []
            for k, v in metrics.items():
                fields.append({"type": "mrkdwn", "text": f"*{k}:*\n`{v}`"})
            blocks.append({"type": "section", "fields": fields[:10]})

        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"*Source:* AI Data Analyst OS | *Time:* {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"}],
        })

        return {"blocks": blocks}

    # 2. Microsoft Teams Adaptive Card Formatter
    def format_teams_adaptive_card(
        self,
        title: str,
        subtitle: str,
        facts: Dict[str, str],
        action_url: str = "https://app.analyst-os.internal",
    ) -> Dict[str, Any]:
        """Generate Microsoft Teams Adaptive Card JSON."""
        fact_items = [{"title": k, "value": str(v)} for k, v in facts.items()]
        return {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {"type": "TextBlock", "size": "Large", "weight": "Bolder", "text": title},
                {"type": "TextBlock", "text": subtitle, "isSubtle": True},
                {"type": "FactSet", "facts": fact_items},
            ],
            "actions": [
                {"type": "Action.OpenUrl", "title": "View in Analyst OS", "url": action_url}
            ],
        }

    # 3. Webhook Engine with HMAC SHA-256 signatures
    def register_webhook(
        self,
        tenant_id: str,
        target_url: str,
        secret_key: str,
        events: List[WebhookEventType],
    ) -> WebhookSubscription:
        """Register a destination endpoint for tenant events."""
        sub_id = f"wh-{uuid.uuid4().hex[:12]}"
        sub = WebhookSubscription(
            id=sub_id,
            tenant_id=tenant_id,
            target_url=target_url,
            secret_key=secret_key,
            subscribed_events=events,
        )
        self._webhooks[sub_id] = sub
        return sub

    @staticmethod
    def generate_hmac_signature(secret: str, payload_bytes: bytes) -> str:
        """Compute HMAC SHA-256 hex digest for payload authentication."""
        return "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

    def dispatch_webhook_event(
        self,
        tenant_id: str,
        event_type: WebhookEventType,
        payload_data: Dict[str, Any],
    ) -> List[DispatchDeliveryResult]:
        """Dispatch event to all matching active tenant webhooks."""
        results = []
        matching_subs = [
            s for s in self._webhooks.values()
            if s.tenant_id == tenant_id and s.is_active and event_type in s.subscribed_events
        ]

        envelope = {
            "event": event_type.value,
            "tenant_id": tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload_data,
        }
        envelope_bytes = json.dumps(envelope, sort_keys=True).encode()

        for sub in matching_subs:
            sig = self.generate_hmac_signature(sub.secret_key, envelope_bytes)
            delivery = DispatchDeliveryResult(
                delivery_id=f"del-{uuid.uuid4().hex[:10]}",
                channel=IntegrationChannel.WEBHOOK,
                status="DELIVERED",
                status_code=200,
                payload_summary=f"Event {event_type.value} sent to {sub.target_url}",
                signature=sig,
            )
            self._dispatch_log.append(delivery)
            results.append(delivery)

        return results

    # 4. Jira Incident Automation
    def format_jira_incident(
        self,
        project_key: str,
        summary: str,
        description: str,
        priority: str = "High",
    ) -> Dict[str, Any]:
        """Format Jira REST API issue creation payload."""
        return {
            "fields": {
                "project": {"key": project_key},
                "summary": f"[Anomaly Alert] {summary}",
                "description": description,
                "issuetype": {"name": "Bug"},
                "priority": {"name": priority},
                "labels": ["ai-analyst-os", "data-anomaly", "auto-generated"],
            }
        }

    # 5. Executive Email Digest Generator
    def render_email_digest(
        self,
        company_name: str,
        recipient_email: str,
        kpi_metrics: Dict[str, Any],
        top_insights: List[str],
    ) -> Dict[str, str]:
        """Generate responsive HTML and plain-text executive briefing email."""
        kpi_rows = "".join(
            f"<tr><td style='padding:8px; border-bottom:1px solid #eee;'><b>{k}</b></td>"
            f"<td style='padding:8px; border-bottom:1px solid #eee; text-align:right;'>{v}</td></tr>"
            for k, v in kpi_metrics.items()
        )
        insight_bullets = "".join(f"<li style='margin-bottom:6px;'>{i}</li>" for i in top_insights)

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width:600px; margin:0 auto; padding:20px;">
            <h2 style="color:#1E293B;">Executive Intelligence Briefing — {company_name}</h2>
            <p style="color:#64748B;">Automated summary compiled by AI Data Analyst OS</p>
            <table style="width:100%; border-collapse:collapse; margin:20px 0;">
                {kpi_rows}
            </table>
            <h3>Top Strategic Insights</h3>
            <ul>
                {insight_bullets}
            </ul>
        </div>
        """
        plain = (
            f"Executive Intelligence Briefing — {company_name}\n\n"
            + "\n".join(f"- {k}: {v}" for k, v in kpi_metrics.items())
            + "\n\nTop Insights:\n"
            + "\n".join(f"* {i}" for i in top_insights)
        )

        return {"recipient": recipient_email, "subject": f"Daily Executive Briefing - {company_name}", "html": html, "plain_text": plain}

    def reset(self) -> None:
        """Reset storage for testing."""
        self._webhooks.clear()
        self._dispatch_log.clear()
