"""AI Quality Monitoring System (Phase 11.4).

Detects performance degradation, hallucinations, syntax/logical SQL errors,
forecast drift, and unsound business recommendations.

Triggers real-time alerts when composite quality falls below SLAs.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Any, Dict, List, Optional


class QualityDefectType(str, Enum):
    HALLUCINATION = "hallucination"
    INCORRECT_SQL = "incorrect_sql"
    WRONG_FORECAST = "wrong_forecast"
    BAD_RECOMMENDATION = "bad_recommendation"
    LATENCY_SPIKE = "latency_spike"


class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class QualityDefect:
    defect_id: str
    defect_type: QualityDefectType
    component: str
    details: str
    severity: AlertSeverity
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class QualityAlert:
    alert_id: str
    defect_type: str
    component: str
    severity: str
    message: str
    current_score: float
    triggered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AIQualityMonitor:
    """Enterprise Quality Monitoring Engine: Defect Tracking & Automated Alerts."""

    DEFECT_PENALTIES = {
        QualityDefectType.INCORRECT_SQL: 8.0,
        QualityDefectType.HALLUCINATION: 10.0,
        QualityDefectType.WRONG_FORECAST: 7.0,
        QualityDefectType.BAD_RECOMMENDATION: 6.0,
        QualityDefectType.LATENCY_SPIKE: 3.0,
    }

    def __init__(self, alert_threshold: float = 90.0) -> None:
        self.alert_threshold = alert_threshold
        self._defects: List[QualityDefect] = []
        self._alerts: List[QualityAlert] = []
        self._total_checks: int = 100

    def record_successful_check(self, count: int = 1) -> None:
        """Record successful agent operations to dilute penalty."""
        self._total_checks += max(1, count)

    def report_defect(
        self,
        defect_type: QualityDefectType | str,
        component: str,
        details: str,
        severity: AlertSeverity = AlertSeverity.HIGH,
    ) -> Dict[str, Any]:
        """Log a quality defect and determine if an alert must be fired."""
        if isinstance(defect_type, str):
            dtype = QualityDefectType(defect_type.lower())
        else:
            dtype = defect_type

        defect = QualityDefect(
            defect_id=f"def_{uuid.uuid4().hex[:10]}",
            defect_type=dtype,
            component=component,
            details=details,
            severity=severity,
        )
        self._defects.append(defect)

        current_score = self.compute_quality_score()
        alert_created = None

        if current_score < self.alert_threshold:
            alert = QualityAlert(
                alert_id=f"alt_{uuid.uuid4().hex[:10]}",
                defect_type=dtype.value,
                component=component,
                severity=severity.value,
                message=f"Quality score dropped to {current_score} (below threshold {self.alert_threshold}): {details}",
                current_score=current_score,
            )
            self._alerts.append(alert)
            alert_created = alert.to_dict()

        return {
            "defect_id": defect.defect_id,
            "quality_score": current_score,
            "alert_triggered": alert_created is not None,
            "alert": alert_created,
        }

    def compute_quality_score(self) -> float:
        """Calculate weighted composite quality score (0.0 to 100.0)."""
        if not self._defects:
            return 100.0

        total_penalty = sum(
            self.DEFECT_PENALTIES.get(d.defect_type, 5.0) for d in self._defects[-50:]
        )
        score = max(0.0, 100.0 - total_penalty)
        return round(score, 1)

    def get_status(self) -> Dict[str, Any]:
        """Return standardized status payload."""
        score = self.compute_quality_score()
        return {
            "quality_score": score,
            "alert_threshold": self.alert_threshold,
            "has_active_alerts": len(self._alerts) > 0,
            "total_defects": len(self._defects),
            "alerts": [a.to_dict() for a in self._alerts],
        }

    def clear(self) -> None:
        self._defects.clear()
        self._alerts.clear()
        self._total_checks = 100


ai_quality_monitor = AIQualityMonitor()
