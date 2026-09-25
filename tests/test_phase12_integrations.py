"""Tests for Phase 12.7 — Enterprise Integrations."""

import pytest
from backend.enterprise.enterprise_integrations import (
    EnterpriseIntegrationHub,
    WebhookEventType,
)


@pytest.fixture(autouse=True)
def reset_integrations():
    hub = EnterpriseIntegrationHub()
    hub.reset()
    yield
    hub.reset()


def test_format_slack_alert():
    hub = EnterpriseIntegrationHub()
    payload = hub.format_slack_alert(
        title="Anomaly Detected: Sudden Revenue Spike",
        message="Revenue increased by 142% between 14:00 and 15:00 UTC.",
        severity="WARNING",
        metrics={"Delta": "+$142,000", "Confidence": "98.2%"},
    )
    assert "blocks" in payload
    assert len(payload["blocks"]) >= 3
    assert "Anomaly Detected" in str(payload)


def test_format_teams_adaptive_card():
    hub = EnterpriseIntegrationHub()
    card = hub.format_teams_adaptive_card(
        title="Daily KPI Briefing",
        subtitle="Growth & Retention Metrics",
        facts={"MRR": "$2.84M", "Net Retention": "118%", "Churn": "0.8%"},
    )
    assert card["type"] == "AdaptiveCard"
    assert len(card["body"]) >= 3
    assert card["body"][0]["text"] == "Daily KPI Briefing"


def test_webhook_hmac_registration_and_dispatch():
    hub = EnterpriseIntegrationHub()
    secret = "super_secure_webhook_secret_key"
    sub = hub.register_webhook(
        tenant_id="tenant-1",
        target_url="https://api.partner.com/webhooks/analyst",
        secret_key=secret,
        events=[WebhookEventType.ANOMALY_DETECTED, WebhookEventType.DATASET_UPLOADED],
    )
    assert sub.id.startswith("wh-")

    # Dispatch anomaly event
    deliveries = hub.dispatch_webhook_event(
        tenant_id="tenant-1",
        event_type=WebhookEventType.ANOMALY_DETECTED,
        payload_data={"dataset": "q3_sales", "anomaly_score": 0.94},
    )
    assert len(deliveries) == 1
    delivery = deliveries[0]
    assert delivery.status == "DELIVERED"
    assert delivery.signature is not None
    assert delivery.signature.startswith("sha256=")


def test_email_digest_and_jira_ticket():
    hub = EnterpriseIntegrationHub()

    # Jira formatting
    jira_payload = hub.format_jira_incident(
        project_key="ANOM",
        summary="Spike in Failed Checkout Webhooks",
        description="Root cause identified as third-party payment timeout.",
    )
    assert jira_payload["fields"]["project"]["key"] == "ANOM"
    assert jira_payload["fields"]["issuetype"]["name"] == "Bug"

    # Email digest
    email = hub.render_email_digest(
        company_name="Acme Global",
        recipient_email="ceo@acme.com",
        kpi_metrics={"Daily Active Users": "48,200", "Conversion": "3.4%"},
        top_insights=["DAU up 12% week-over-week", "Checkout conversion healthy"],
    )
    assert email["recipient"] == "ceo@acme.com"
    assert "Daily Active Users" in email["html"]
    assert "Acme Global" in email["plain_text"]
