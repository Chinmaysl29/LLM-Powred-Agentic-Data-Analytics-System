"""
Phase 12.8 — Mobile Platform Package Exports
"""

from backend.mobile.architecture import (
    MobileArchitectureManager,
    MobileAppConfig,
    MobileDeviceProfile,
    MobileOS,
    DeviceType,
)
from backend.mobile.auth import (
    MobileAuthManager,
    MobileSession,
)
from backend.mobile.dashboard import (
    MobileDashboardService,
    MobileKPICard,
    MobileChartPayload,
    MobileDashboardResponse,
)
from backend.mobile.chat import (
    MobileAIChatService,
    MobileChatMessage,
    MobileChatThread,
)
from backend.mobile.reports import (
    MobileReportsService,
    MobileReportItem,
)
from backend.mobile.forecasting import (
    MobileForecastingService,
    MobileForecastModel,
    MobileForecastScenario,
)
from backend.mobile.notifications import (
    MobileNotificationService,
    MobileNotification,
)
from backend.mobile.offline_sync import (
    OfflineSyncEngine,
    ConflictStrategy,
    SyncQueueItem,
)
from backend.mobile.analytics import (
    MobileAnalyticsEngine,
    MobileTelemetryEvent,
    MobilePerformanceMetric,
    MobileCrashReport,
)

__all__ = [
    "MobileArchitectureManager",
    "MobileAppConfig",
    "MobileDeviceProfile",
    "MobileOS",
    "DeviceType",
    "MobileAuthManager",
    "MobileSession",
    "MobileDashboardService",
    "MobileKPICard",
    "MobileChartPayload",
    "MobileDashboardResponse",
    "MobileAIChatService",
    "MobileChatMessage",
    "MobileChatThread",
    "MobileReportsService",
    "MobileReportItem",
    "MobileForecastingService",
    "MobileForecastModel",
    "MobileForecastScenario",
    "MobileNotificationService",
    "MobileNotification",
    "OfflineSyncEngine",
    "ConflictStrategy",
    "SyncQueueItem",
    "MobileAnalyticsEngine",
    "MobileTelemetryEvent",
    "MobilePerformanceMetric",
    "MobileCrashReport",
]
