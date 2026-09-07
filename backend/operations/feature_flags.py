"""Feature Flag System (Phase 11.6).

Safely controls feature releases and rollouts:
- Beta Features
- Experimental Agents
- New Dashboard Widgets
- New Machine Learning Models

Supports:
- Boolean toggling
- User role/group targeting (e.g. admin, beta_tester)
- Percentage rollouts (0-100%)
- Kill-switch overrides
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Optional, Set


@dataclass
class FeatureFlag:
    name: str
    description: str
    enabled: bool = False
    rollout_percentage: int = 100
    allowed_roles: Set[str] = field(default_factory=set)
    allowed_users: Set[str] = field(default_factory=set)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "rollout_percentage": self.rollout_percentage,
            "allowed_roles": list(self.allowed_roles),
            "allowed_users": list(self.allowed_users),
            "updated_at": self.updated_at,
        }


class FeatureFlagSystem:
    """Enterprise Feature Flag & Dynamic Configuration Engine."""

    def __init__(self) -> None:
        self._flags: Dict[str, FeatureFlag] = {}
        self._init_defaults()

    def _init_defaults(self) -> None:
        """Register initial system flags."""
        self.register_flag(
            name="experimental_agents",
            description="Access to experimental autonomous decision agents",
            enabled=False,
            allowed_roles={"admin", "beta_tester"},
        )
        self.register_flag(
            name="new_dashboard_widgets",
            description="Enhanced real-time time-series visualizer widgets",
            enabled=True,
            rollout_percentage=100,
        )
        self.register_flag(
            name="xgboost_forecaster_v2",
            description="Ultra-fast XGBoost forecaster engine with cross-validation",
            enabled=True,
            rollout_percentage=50,
        )
        self.register_flag(
            name="advanced_rag_hybrid",
            description="Multi-retriever hybrid semantic search",
            enabled=True,
        )

    def register_flag(
        self,
        name: str,
        description: str,
        enabled: bool = False,
        rollout_percentage: int = 100,
        allowed_roles: Optional[Set[str]] = None,
        allowed_users: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """Create or update a feature flag."""
        flag = FeatureFlag(
            name=name,
            description=description,
            enabled=enabled,
            rollout_percentage=max(0, min(100, rollout_percentage)),
            allowed_roles=allowed_roles or set(),
            allowed_users=allowed_users or set(),
        )
        self._flags[name] = flag
        return flag.to_dict()

    def set_enabled(self, name: str, enabled: bool) -> Dict[str, Any]:
        if name not in self._flags:
            raise KeyError(f"Feature flag '{name}' not found")
        self._flags[name].enabled = enabled
        self._flags[name].updated_at = datetime.now(timezone.utc).isoformat()
        return self._flags[name].to_dict()

    def is_enabled(
        self,
        feature_name: str,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate whether a feature is active for the given context."""
        flag = self._flags.get(feature_name)
        if not flag:
            return {"feature": feature_name, "enabled": False, "reason": "flag_not_found"}

        # Master kill-switch check
        if not flag.enabled:
            return {"feature": feature_name, "enabled": False, "reason": "flag_disabled"}

        # User ID override
        if user_id and user_id in flag.allowed_users:
            return {"feature": feature_name, "enabled": True, "reason": "user_allowlist"}

        # Role override
        if role and role in flag.allowed_roles:
            return {"feature": feature_name, "enabled": True, "reason": "role_allowlist"}

        # If role restrictions exist but caller does not have an allowed role
        if flag.allowed_roles and (not role or role not in flag.allowed_roles):
            return {"feature": feature_name, "enabled": False, "reason": "role_restricted"}

        # Percentage rollout check (deterministic per user_id if provided)
        if flag.rollout_percentage < 100:
            if user_id:
                bucket = int(hashlib.md5(f"{feature_name}:{user_id}".encode("utf-8")).hexdigest()[:4], 16) % 100
                is_active = bucket < flag.rollout_percentage
                return {
                    "feature": feature_name,
                    "enabled": is_active,
                    "reason": "rollout_bucket" if is_active else "rollout_excluded",
                }
            return {
                "feature": feature_name,
                "enabled": False,
                "reason": "user_id_required_for_percentage_rollout",
            }

        return {"feature": feature_name, "enabled": True, "reason": "fully_enabled"}

    def get_all_flags(self) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self._flags.values()]

    def clear(self) -> None:
        self._flags.clear()


feature_flag_system = FeatureFlagSystem()
