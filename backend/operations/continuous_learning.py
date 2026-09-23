"""Continuous Learning Pipeline (Phase 11.8).

Harvests feedback, query corrections, forecast residuals, and recommendation ratings
to generate automated improvement actions and prompt/model enhancements over time.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Any, Dict, List, Optional


class LearningSource(str, Enum):
    USER_FEEDBACK = "user_feedback"
    QUERY_HISTORY = "query_history"
    FORECAST_ACCURACY = "forecast_accuracy"
    RECOMMENDATION_OUTCOME = "recommendation_outcome"


class ActionType(str, Enum):
    PROMPT_REFINEMENT = "PROMPT_REFINEMENT"
    FEW_SHOT_UPDATE = "FEW_SHOT_UPDATE"
    SCHEMA_SYNONYM_ADDITION = "SCHEMA_SYNONYM_ADDITION"
    HYPERPARAMETER_TUNING = "HYPERPARAMETER_TUNING"
    INDEX_REBUILD = "INDEX_REBUILD"


@dataclass
class LearningEvent:
    event_id: str
    source: LearningSource
    target_component: str
    original_input: str
    user_correction: Optional[str] = None
    rating: Optional[int] = None  # 1-5 or -1/+1
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ImprovementAction:
    action_id: str
    target: str
    action_type: ActionType
    description: str
    priority: str
    status: str = "PENDING"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["action_type"] = self.action_type.value
        return d


class ContinuousLearningPipeline:
    """Enterprise Continuous Learning & Self-Improving Pipeline."""

    def __init__(self) -> None:
        self._events: List[LearningEvent] = []
        self._actions: List[ImprovementAction] = []

    def record_learning_event(
        self,
        source: LearningSource | str,
        target_component: str,
        original_input: str,
        user_correction: Optional[str] = None,
        rating: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record an instance of user correction, failure, or rating."""
        src = LearningSource(source.lower()) if isinstance(source, str) else source
        event = LearningEvent(
            event_id=f"learn_{uuid.uuid4().hex[:10]}",
            source=src,
            target_component=target_component,
            original_input=original_input,
            user_correction=user_correction,
            rating=rating,
            metadata=metadata or {},
        )
        self._events.append(event)

        # Trigger synthesis of improvements based on recent events
        self._synthesize_actions()

        return {
            "event_id": event.event_id,
            "source": src.value,
            "target_component": target_component,
            "recorded_at": event.timestamp,
        }

    def _synthesize_actions(self) -> None:
        """Analyze learning events for recurring failure clusters and generate concrete actions."""
        # 1. Check for recurring SQL corrections
        sql_corrections = [
            e for e in self._events
            if e.target_component in ("sql_agent", "text_to_sql") and e.user_correction
        ]
        if len(sql_corrections) >= 2:
            action_desc = f"Repeated SQL corrections ({len(sql_corrections)} events) detected. Add few-shot examples for date/aggregation handling."
            if not any(a.description == action_desc for a in self._actions):
                self._actions.append(ImprovementAction(
                    action_id=f"act_{uuid.uuid4().hex[:8]}",
                    target="sql_agent",
                    action_type=ActionType.FEW_SHOT_UPDATE,
                    description=action_desc,
                    priority="HIGH",
                ))

        # 2. Check for negative forecast ratings
        forecast_negatives = [
            e for e in self._events
            if e.target_component in ("forecast_agent", "forecasting") and (e.rating is not None and e.rating <= 2)
        ]
        if len(forecast_negatives) >= 2:
            action_desc = f"Multiple negative forecast ratings ({len(forecast_negatives)} events). Re-calibrate hyperparameter grids and confidence interval intervals."
            if not any(a.description == action_desc for a in self._actions):
                self._actions.append(ImprovementAction(
                    action_id=f"act_{uuid.uuid4().hex[:8]}",
                    target="forecast_agent",
                    action_type=ActionType.HYPERPARAMETER_TUNING,
                    description=action_desc,
                    priority="MEDIUM",
                ))

        # 3. Check for repeated recommendation corrections
        rec_events = [
            e for e in self._events
            if e.target_component in ("recommendation_agent", "decision_agent") and e.user_correction
        ]
        if len(rec_events) >= 2:
            action_desc = "User override on business recommendations. Refine prompt constraints regarding risk tolerance."
            if not any(a.description == action_desc for a in self._actions):
                self._actions.append(ImprovementAction(
                    action_id=f"act_{uuid.uuid4().hex[:8]}",
                    target="recommendation_agent",
                    action_type=ActionType.PROMPT_REFINEMENT,
                    description=action_desc,
                    priority="HIGH",
                ))

    def get_improvements(self) -> Dict[str, Any]:
        """Return synthesized improvement actions."""
        # Ensure at least a baseline recommendation exists if actions are empty
        actions = [a.to_dict() for a in self._actions]
        if not actions:
            actions = [{
                "action_id": "act_baseline_01",
                "target": "platform_wide",
                "action_type": ActionType.PROMPT_REFINEMENT.value,
                "description": "Continuous monitoring active; no anomalous failure clusters detected.",
                "priority": "LOW",
                "status": "MONITORING",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }]

        return {
            "total_learning_events": len(self._events),
            "improvement_actions": actions,
        }

    def clear(self) -> None:
        self._events.clear()
        self._actions.clear()


continuous_learning_pipeline = ContinuousLearningPipeline()
