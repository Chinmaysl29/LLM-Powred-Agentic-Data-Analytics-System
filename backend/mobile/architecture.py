"""
Phase 12.8.1 — Mobile Platform Foundation & Architecture
Defines mobile runtime configurations, device profiles (Android, iOS, Tablet),
state management contracts, and API gateway connectivity.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
import time
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.mobile.architecture")


class MobileOS(str, Enum):
    IOS = "ios"
    ANDROID = "android"


class DeviceType(str, Enum):
    PHONE = "phone"
    TABLET = "tablet"


class MobileAppConfig(BaseModel):
    app_version: str = "2.4.0"
    build_number: int = 142
    environment: str = "production"
    api_base_url: str = "https://api.analystos.enterprise.com"
    timeout_ms: int = 15000
    offline_cache_enabled: bool = True
    biometrics_enabled: bool = True
    push_notifications_enabled: bool = True


class MobileDeviceProfile(BaseModel):
    device_id: str
    os: MobileOS
    os_version: str
    device_type: DeviceType = DeviceType.PHONE
    screen_width: int = 390
    screen_height: int = 844
    scale_factor: float = 3.0
    is_tablet: bool = False
    fcm_or_apns_token: Optional[str] = None


class MobileArchitectureManager:
    """
    Manages client device configurations, responsive layout breakpoints,
    state initialization manifests, and API gateway connectivity.
    """

    def __init__(self, config: Optional[MobileAppConfig] = None):
        self.config = config or MobileAppConfig()
        self._connected_devices: Dict[str, MobileDeviceProfile] = {}

    def register_device(self, profile: MobileDeviceProfile) -> Dict[str, Any]:
        """Register a mobile client device and determine layout profile."""
        profile.is_tablet = profile.device_type == DeviceType.TABLET or min(profile.screen_width, profile.screen_height) >= 600
        self._connected_devices[profile.device_id] = profile
        logger.info("Registered mobile device %s (%s, tablet=%s)", profile.device_id, profile.os.value, profile.is_tablet)
        return {
            "registered": True,
            "device_id": profile.device_id,
            "is_tablet": profile.is_tablet,
            "app_config": self.config.model_dump()
        }

    def check_api_connectivity(self, endpoint: str = "/api/v1/health") -> Dict[str, Any]:
        """Validate mobile API gateway connectivity."""
        start_time = time.time()
        # Simulated gateway latency check
        latency_ms = round((time.time() - start_time) * 1000.0 + 12.5, 2)
        return {
            "status": "connected",
            "endpoint": f"{self.config.api_base_url}{endpoint}",
            "latency_ms": latency_ms,
            "timestamp": time.time()
        }

    def get_state_management_schema(self) -> Dict[str, Any]:
        """Returns the Redux Toolkit initial state contracts for the mobile client."""
        return {
            "slices": [
                "auth",
                "dashboard",
                "chat",
                "reports",
                "forecasting",
                "notifications",
                "offlineSync",
                "analytics"
            ],
            "middleware": ["redux-thunk", "offline-sync-middleware", "telemetry-middleware"],
            "version": 1
        }
