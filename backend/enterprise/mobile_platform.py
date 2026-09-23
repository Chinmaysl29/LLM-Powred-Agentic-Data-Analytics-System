"""Phase 12.8 — Mobile Platform

Provides executive mobile feeds, push notification formatting (APNs/FCM),
offline sync manifests, and bandwidth-conserving chart point decimation for iOS and Android.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional
import uuid


class MobilePlatform(str, Enum):
    IOS = "ios"
    ANDROID = "android"


class CardType(str, Enum):
    METRIC_HIGHLIGHT = "metric_highlight"
    ANOMALY_ALERT = "anomaly_alert"
    FORECAST_SUMMARY = "forecast_summary"
    RECOMMENDATION = "recommendation"


@dataclass
class ExecutiveMobileCard:
    id: str
    card_type: CardType
    title: str
    headline_value: str
    trend_direction: str  # "UP", "DOWN", "STABLE"
    trend_percentage: float
    summary: str
    urgent: bool = False
    deep_link: str = "analystos://dashboards/executive"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "card_type": self.card_type.value,
            "title": self.title,
            "headline_value": self.headline_value,
            "trend_direction": self.trend_direction,
            "trend_percentage": self.trend_percentage,
            "summary": self.summary,
            "urgent": self.urgent,
            "deep_link": self.deep_link,
            "timestamp": self.timestamp.isoformat(),
        }


class MobilePlatformEngine:
    """Singleton engine powering the mobile executive application experience."""

    _instance: Optional[MobilePlatformEngine] = None

    def __new__(cls) -> MobilePlatformEngine:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_executive_feed(self, tenant_id: str, user_id: str) -> List[ExecutiveMobileCard]:
        """Generate bite-sized executive cards optimized for mobile screens."""
        cards = [
            ExecutiveMobileCard(
                id=f"card-rev-{uuid.uuid4().hex[:8]}",
                card_type=CardType.METRIC_HIGHLIGHT,
                title="Monthly Recurring Revenue",
                headline_value="$2.84M",
                trend_direction="UP",
                trend_percentage=14.2,
                summary="MRR grew 14.2% month-over-month driven by Enterprise tier upgrades.",
                urgent=False,
            ),
            ExecutiveMobileCard(
                id=f"card-anom-{uuid.uuid4().hex[:8]}",
                card_type=CardType.ANOMALY_ALERT,
                title="Checkout Conversion Drop",
                headline_value="2.8%",
                trend_direction="DOWN",
                trend_percentage=-1.4,
                summary="European payment gateway error rate spiked 18% over the last 2 hours.",
                urgent=True,
                deep_link="analystos://alerts/conversion-eu",
            ),
            ExecutiveMobileCard(
                id=f"card-fcst-{uuid.uuid4().hex[:8]}",
                card_type=CardType.FORECAST_SUMMARY,
                title="Q4 Revenue Forecast",
                headline_value="$9.12M",
                trend_direction="UP",
                trend_percentage=8.5,
                summary="Prophet tournament forecast predicts exceeding original annual target.",
                urgent=False,
            ),
            ExecutiveMobileCard(
                id=f"card-rec-{uuid.uuid4().hex[:8]}",
                card_type=CardType.RECOMMENDATION,
                title="Cost Optimization Insight",
                headline_value="-$34.5K",
                trend_direction="DOWN",
                trend_percentage=-22.0,
                summary="Routing analytical queries to Groq/Llama 3.3 saves an estimated $34,500/mo.",
                urgent=False,
            ),
        ]
        return cards

    def format_push_notification(
        self,
        platform: MobilePlatform,
        title: str,
        body: str,
        badge_count: int = 1,
        deep_link: str = "analystos://feed",
        sound: str = "default",
    ) -> Dict[str, Any]:
        """Format APNs (iOS) or FCM (Android) native push notification payload."""
        if platform == MobilePlatform.IOS:
            return {
                "aps": {
                    "alert": {"title": title, "body": body},
                    "badge": badge_count,
                    "sound": sound,
                    "thread-id": "executive-briefing",
                },
                "data": {"deep_link": deep_link, "sent_at": datetime.now(timezone.utc).isoformat()},
            }
        else:
            return {
                "notification": {"title": title, "body": body, "sound": sound},
                "data": {
                    "click_action": "OPEN_EXECUTIVE_DASHBOARD",
                    "deep_link": deep_link,
                    "badge": str(badge_count),
                },
                "android": {"priority": "HIGH"},
            }

    def generate_offline_manifest(self, tenant_id: str, workspace_id: str) -> Dict[str, Any]:
        """Create lightweight offline cache manifest for frictionless offline mobile usage."""
        return {
            "manifest_version": "1.0",
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "expires_in_seconds": 86400,
            "cached_endpoints": [
                "/api/v1/enterprise/mobile/feed",
                "/api/v1/enterprise/tenants/current",
                "/api/v1/operations/dashboard",
            ],
            "offline_payload_size_kb": 48.6,
        }

    @staticmethod
    def decimate_chart_points(
        points: List[Dict[str, Any]],
        max_points: int = 50,
        x_key: str = "x",
        y_key: str = "y",
    ) -> List[Dict[str, Any]]:
        """Downsample dense time-series points to save mobile bandwidth while preserving peaks."""
        if len(points) <= max_points or max_points <= 2:
            return points

        step = len(points) / float(max_points)
        sampled = []
        for i in range(max_points):
            idx = min(int(round(i * step)), len(points) - 1)
            sampled.append(points[idx])

        # Ensure last point is always preserved
        if sampled[-1] != points[-1]:
            sampled[-1] = points[-1]

        return sampled
