"""Phase 12.5.1 — Domain Agent Framework.

Abstract enterprise agent interface and standardized output contracts for
domain-specialized analytics agents.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import enum
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class DomainSeverity(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class DomainInsight:
    id: str = field(default_factory=lambda: f"ins-{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    domain: str = "general"
    severity: DomainSeverity = DomainSeverity.INFO
    metrics: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.95


@dataclass
class DomainRisk:
    id: str = field(default_factory=lambda: f"rsk-{uuid.uuid4().hex[:8]}")
    category: str = "operational"
    risk_score: float = 0.0  # 0 to 100
    impact: str = "MEDIUM"
    description: str = ""
    mitigation: str = ""


@dataclass
class DomainRecommendation:
    id: str = field(default_factory=lambda: f"rec-{uuid.uuid4().hex[:8]}")
    title: str = ""
    action: str = ""
    impact: str = "HIGH"
    effort: str = "MEDIUM"
    expected_outcome: str = ""
    priority: int = 1


@dataclass
class DomainAnalysisResult:
    agent_name: str
    domain: str
    summary: str
    kpis: Dict[str, Any] = field(default_factory=dict)
    insights: List[DomainInsight] = field(default_factory=list)
    risks: List[DomainRisk] = field(default_factory=list)
    recommendations: List[DomainRecommendation] = field(default_factory=list)
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "domain": self.domain,
            "summary": self.summary,
            "kpis": self.kpis,
            "insights": [
                {
                    "id": i.id,
                    "title": i.title,
                    "description": i.description,
                    "severity": i.severity.value,
                    "metrics": i.metrics,
                    "confidence": i.confidence,
                }
                for i in self.insights
            ],
            "risks": [
                {
                    "id": r.id,
                    "category": r.category,
                    "risk_score": r.risk_score,
                    "impact": r.impact,
                    "description": r.description,
                    "mitigation": r.mitigation,
                }
                for r in self.risks
            ],
            "recommendations": [
                {
                    "id": rc.id,
                    "title": rc.title,
                    "action": rc.action,
                    "impact": rc.impact,
                    "effort": rc.effort,
                    "expected_outcome": rc.expected_outcome,
                    "priority": rc.priority,
                }
                for rc in self.recommendations
            ],
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseDomainAgent(ABC):
    """Abstract base class for all enterprise domain-specialized analytical agents."""

    def __init__(self, name: str, domain: str) -> None:
        self.name = name
        self.domain = domain

    @abstractmethod
    def analyze(
        self,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> DomainAnalysisResult:
        """Execute end-to-end domain analytical processing."""
        pass

    @abstractmethod
    def generate_insights(self, data: Dict[str, Any]) -> List[DomainInsight]:
        """Extract domain-specific analytical patterns and anomalies."""
        pass

    @abstractmethod
    def generate_recommendations(
        self,
        data: Dict[str, Any],
        insights: List[DomainInsight],
    ) -> List[DomainRecommendation]:
        """Produce actionable and strategic business recommendations."""
        pass

    @abstractmethod
    def generate_summary(
        self,
        data: Dict[str, Any],
        insights: List[DomainInsight],
    ) -> str:
        """Generate human-readable executive briefing summary."""
        pass

    def validate_results(self, results: DomainAnalysisResult) -> bool:
        """Validate result completeness, metrics sanity, and contract conformity."""
        if not results.agent_name or not results.domain:
            return False
        if not results.summary:
            return False
        if not isinstance(results.kpis, dict):
            return False
        return True
