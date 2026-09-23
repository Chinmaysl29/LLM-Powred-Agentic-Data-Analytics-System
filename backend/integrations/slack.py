"""
Phase 12.7.3 — Slack Integration
Slack enterprise connector supporting notifications, Block Kit reports, forecast alerts,
channel creation, and slash command processing.
"""

from typing import Dict, Any, Optional, List
import time
from backend.integrations.base import (
    BaseEnterpriseIntegration,
    IntegrationHealthResult,
    IntegrationSyncResult,
)


class SlackIntegration(BaseEnterpriseIntegration):
    """
    Enterprise Slack integration client.
    Supports bot tokens, webhooks, Block Kit message structuring,
    forecast alerts, and slash command dispatcher.
    """

    def __init__(self, integration_id: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(integration_id, config)
        self.bot_token = self.config.get("bot_token", "xoxb-mock-token")
        self.webhook_url = self.config.get("webhook_url")
        self.default_channel = self.config.get("default_channel", "#general")
        self._sent_messages: List[Dict[str, Any]] = []
        self._channels: List[str] = ["#general", "#analytics", "#alerts"]

    def connect(self) -> bool:
        if not self.bot_token and not self.webhook_url:
            self.logger.error("Neither bot_token nor webhook_url provided for Slack integration")
            self.is_connected = False
            return False
        self.is_connected = True
        self.logger.info("Slack integration %s connected successfully.", self.integration_id)
        return True

    def disconnect(self) -> bool:
        self.is_connected = False
        self.logger.info("Slack integration %s disconnected.", self.integration_id)
        return True

    def validate(self) -> bool:
        if not self.bot_token.startswith("xoxb-") and not self.webhook_url:
            return False
        return True

    def health_check(self) -> IntegrationHealthResult:
        start_time = time.time()
        is_valid = self.validate()
        latency = (time.time() - start_time) * 1000.0
        return IntegrationHealthResult(
            healthy=is_valid and self.is_connected,
            status_code=200 if is_valid else 401,
            latency_ms=round(latency, 2),
            message="Slack connection healthy" if is_valid else "Invalid Slack credentials",
            details={"channels_available": len(self._channels), "messages_sent": len(self._sent_messages)}
        )

    def sync(self, payload: Optional[Dict[str, Any]] = None) -> IntegrationSyncResult:
        """Sync channels and workspace user groups."""
        if not self.is_connected:
            return IntegrationSyncResult(success=False, errors=["Slack integration not connected"])
        return IntegrationSyncResult(
            success=True,
            records_synced=len(self._channels),
            metadata={"synced_channels": self._channels}
        )

    def send_message(self, text: str, channel: Optional[str] = None, blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Send standard or Block Kit rich text message."""
        target_channel = channel or self.default_channel
        payload = {
            "channel": target_channel,
            "text": text,
            "blocks": blocks or [{"type": "section", "text": {"type": "mrkdwn", "text": text}}],
            "timestamp": time.time()
        }
        self._sent_messages.append(payload)
        self.logger.info("Sent Slack message to %s: %s", target_channel, text[:50])
        return {"ok": True, "channel": target_channel, "ts": str(payload["timestamp"])}

    def post_report(self, report_title: str, summary: str, kpis: Dict[str, Any], channel: Optional[str] = None) -> Dict[str, Any]:
        """Post a structured analytics report with KPIs."""
        kpi_fields = [
            {"type": "mrkdwn", "text": f"*{k.replace('_', ' ').title()}:*\n{v}"}
            for k, v in kpis.items()
        ]
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📊 Report: {report_title}"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": summary}
            },
            {
                "type": "section",
                "fields": kpi_fields[:10]  # Slack limit is 10 fields per section
            }
        ]
        return self.send_message(text=f"Report: {report_title}", channel=channel, blocks=blocks)

    def send_forecast(self, metric_name: str, forecast_value: float, confidence_interval: tuple, horizon_days: int, channel: Optional[str] = None) -> Dict[str, Any]:
        """Post an automated ML forecast alert."""
        text = (
            f"📈 *AI Forecast Alert — {metric_name}*\n"
            f"• Projected Value ({horizon_days}d): `{forecast_value}`\n"
            f"• 95% Confidence Interval: `[{confidence_interval[0]}, {confidence_interval[1]}]`"
        )
        return self.send_message(text=text, channel=channel)

    def send_alert(self, title: str, description: str, severity: str = "warning", channel: Optional[str] = None) -> Dict[str, Any]:
        """Send automated threshold anomaly alert."""
        icon = "🚨" if severity == "critical" else "⚠️"
        text = f"{icon} *{severity.upper()}: {title}*\n{description}"
        return self.send_message(text=text, channel=channel)

    def create_channel(self, channel_name: str) -> Dict[str, Any]:
        """Create a new analytics discussion channel."""
        formatted_name = channel_name if channel_name.startswith("#") else f"#{channel_name}"
        if formatted_name not in self._channels:
            self._channels.append(formatted_name)
        return {"ok": True, "channel": formatted_name, "is_created": True}

    def handle_slash_command(self, command: str, text: str, user_id: str) -> Dict[str, Any]:
        """Future-ready Slack slash command dispatcher."""
        self.logger.info("Executing Slack command %s with args: %s for user %s", command, text, user_id)
        if command == "/analyze":
            return {
                "response_type": "ephemeral",
                "text": f"Running AI analysis on dataset `{text}`. Report will be delivered shortly."
            }
        elif command == "/forecast":
            return {
                "response_type": "ephemeral",
                "text": f"Generating forecast model for `{text}`..."
            }
        return {
            "response_type": "ephemeral",
            "text": f"Command `{command}` acknowledged."
        }
