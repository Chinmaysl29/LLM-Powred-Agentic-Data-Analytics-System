"""In-process alert evaluation with threshold validation and suppression."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import uuid4


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class AlertRule:
    name: str
    threshold: float
    severity: AlertSeverity = AlertSeverity.WARNING
    cooldown_seconds: int = 300


@dataclass
class Alert:
    rule: str
    value: float
    severity: AlertSeverity
    message: str
    alert_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AlertManager:
    def __init__(self) -> None:
        self.rules: dict[str, AlertRule] = {}
        self.history: list[Alert] = []
        self._last_fired: dict[str, datetime] = {}

    def add_rule(self, rule: AlertRule) -> None:
        if rule.threshold < 0 or rule.cooldown_seconds < 0:
            raise ValueError("Alert thresholds and cooldowns must be non-negative")
        self.rules[rule.name] = rule

    def evaluate(self, rule_name: str, value: float, message: str | None = None) -> Alert | None:
        rule = self.rules[rule_name]
        if value < rule.threshold:
            return None
        now = datetime.now(timezone.utc)
        last_fired = self._last_fired.get(rule_name)
        if last_fired and now - last_fired < timedelta(seconds=rule.cooldown_seconds):
            return None
        alert = Alert(rule_name, value, rule.severity, message or f"{rule_name} reached {value}")
        self.history.append(alert)
        self._last_fired[rule_name] = now
        return alert
