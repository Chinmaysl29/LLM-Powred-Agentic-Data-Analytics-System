"""Tests for Phase 12.8 — Mobile Platform."""

import pytest
from backend.enterprise.mobile_platform import (
    MobilePlatform,
    MobilePlatformEngine,
)


def test_executive_feed_generation():
    engine = MobilePlatformEngine()
    feed = engine.get_executive_feed(tenant_id="tenant-1", user_id="usr-exec")
    assert len(feed) >= 4
    # Verify card attributes
    cards_types = [c.card_type.value for c in feed]
    assert "metric_highlight" in cards_types
    assert "anomaly_alert" in cards_types
    assert any(c.urgent for c in feed)


def test_push_notification_payloads():
    engine = MobilePlatformEngine()

    # iOS APNs payload
    apns = engine.format_push_notification(
        platform=MobilePlatform.IOS,
        title="Revenue Alert",
        body="Q4 target exceeded by 8%",
        badge_count=2,
    )
    assert "aps" in apns
    assert apns["aps"]["alert"]["title"] == "Revenue Alert"
    assert apns["aps"]["badge"] == 2

    # Android FCM payload
    fcm = engine.format_push_notification(
        platform=MobilePlatform.ANDROID,
        title="Inventory Low",
        body="SKU 104 below reorder point",
    )
    assert "notification" in fcm
    assert fcm["android"]["priority"] == "HIGH"


def test_offline_manifest():
    engine = MobilePlatformEngine()
    manifest = engine.generate_offline_manifest(tenant_id="tenant-1", workspace_id="ws-1")
    assert manifest["manifest_version"] == "1.0"
    assert len(manifest["cached_endpoints"]) >= 2
    assert manifest["offline_payload_size_kb"] > 0


def test_chart_decimation():
    engine = MobilePlatformEngine()
    # 500 points
    dense_points = [{"x": i, "y": i * 1.5} for i in range(500)]
    decimated = engine.decimate_chart_points(dense_points, max_points=50)

    assert len(decimated) == 50
    assert decimated[0]["x"] == 0
    assert decimated[-1]["x"] == 499
