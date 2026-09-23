"""User Feedback Intelligence System (Phase 11.1).

Captures, categorizes, prioritizes, and analyzes user feedback from multiple channels:
- Chat Feedback
- Dashboard Feedback
- Report Feedback
- Feature Requests
- Bug Reports
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re
import uuid
from typing import Any, Dict, List, Optional


class FeedbackChannel(str, Enum):
    CHAT = "chat"
    DASHBOARD = "dashboard"
    REPORT = "report"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"


class FeedbackCategory(str, Enum):
    PERFORMANCE = "PERFORMANCE"
    BUG = "BUG"
    FEATURE_REQUEST = "FEATURE_REQUEST"
    USABILITY = "USABILITY"
    ACCURACY = "ACCURACY"
    GENERAL = "GENERAL"


class FeedbackPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class FeedbackItem:
    feedback_id: str
    channel: FeedbackChannel
    description: str
    feedback_type: FeedbackCategory
    priority: FeedbackPriority
    user_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["channel"] = self.channel.value
        d["feedback_type"] = self.feedback_type.value
        d["priority"] = self.priority.value
        return d


class FeedbackClassifier:
    """Intelligent rule and NLP classifier for feedback categorization and priority."""

    KEYWORD_MAP = {
        FeedbackCategory.PERFORMANCE: [
            "slow", "latency", "lag", "hang", "timeout", "freeze", "delay",
            "taking forever", "sluggish", "speed", "unresponsive"
        ],
        FeedbackCategory.BUG: [
            "bug", "crash", "error", "broken", "fail", "500", "404", "exception",
            "glitch", "wrong", "doesn't work", "cannot load", "blank page"
        ],
        FeedbackCategory.FEATURE_REQUEST: [
            "feature", "would like", "can we add", "please add", "suggestion",
            "support for", "integrate", "export to", "wish", "new option"
        ],
        FeedbackCategory.ACCURACY: [
            "incorrect", "hallucination", "wrong number", "bad sql", "math error",
            "inaccurate", "wrong forecast", "contradictory"
        ],
        FeedbackCategory.USABILITY: [
            "confusing", "hard to use", "unintuitive", "cannot find", "cluttered",
            "ui", "ux", "layout", "font", "navigation"
        ],
    }

    CRITICAL_TRIGGERS = [
        "crash", "down", "data loss", "corrupt", "leak", "security", "unusable",
        "catastrophic", "500 internal server error", "emergency"
    ]
    HIGH_TRIGGERS = [
        "slow", "broken", "cannot export", "failed", "incorrect calculation",
        "hallucination", "urgent", "wrong numbers"
    ]
    LOW_TRIGGERS = [
        "minor", "typo", "nice to have", "cosmetic", "color", "would be cool"
    ]

    @classmethod
    def classify_category(cls, text: str, explicit_channel: Optional[FeedbackChannel] = None) -> FeedbackCategory:
        lower = text.lower()
        if explicit_channel == FeedbackChannel.BUG_REPORT:
            return FeedbackCategory.BUG
        if explicit_channel == FeedbackChannel.FEATURE_REQUEST:
            return FeedbackCategory.FEATURE_REQUEST

        for cat, keywords in cls.KEYWORD_MAP.items():
            if any(re.search(r"\b" + re.escape(kw) + r"\b", lower) for kw in keywords):
                return cat
        return FeedbackCategory.GENERAL

    @classmethod
    def evaluate_priority(cls, text: str, category: FeedbackCategory) -> FeedbackPriority:
        lower = text.lower()
        if any(w in lower for w in cls.CRITICAL_TRIGGERS):
            return FeedbackPriority.CRITICAL
        if any(w in lower for w in cls.HIGH_TRIGGERS) or category in (FeedbackCategory.PERFORMANCE, FeedbackCategory.BUG, FeedbackCategory.ACCURACY):
            return FeedbackPriority.HIGH
        if any(w in lower for w in cls.LOW_TRIGGERS) or category == FeedbackCategory.GENERAL:
            return FeedbackPriority.LOW
        return FeedbackPriority.MEDIUM


class UserFeedbackIntelligence:
    """Enterprise Feedback Engine: Ingestion, Categorization, Storage & Analytics."""

    def __init__(self) -> None:
        self._store: Dict[str, FeedbackItem] = {}

    def capture_feedback(
        self,
        description: str,
        channel: FeedbackChannel | str = FeedbackChannel.DASHBOARD,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Capture user feedback, auto-classify type and priority, and persist."""
        if not description or not description.strip():
            raise ValueError("Feedback description cannot be empty")

        if isinstance(channel, str):
            try:
                ch = FeedbackChannel(channel.lower())
            except ValueError:
                ch = FeedbackChannel.DASHBOARD
        else:
            ch = channel

        feedback_type = FeedbackClassifier.classify_category(description, explicit_channel=ch)
        priority = FeedbackClassifier.evaluate_priority(description, feedback_type)
        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"

        item = FeedbackItem(
            feedback_id=feedback_id,
            channel=ch,
            description=description.strip(),
            feedback_type=feedback_type,
            priority=priority,
            user_id=user_id,
            metadata=metadata or {},
        )
        self._store[feedback_id] = item

        return {
            "feedback_id": item.feedback_id,
            "feedback_type": item.feedback_type.value,
            "priority": item.priority.value,
            "description": item.description,
            "channel": item.channel.value,
            "created_at": item.created_at,
        }

    def get_feedback(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        item = self._store.get(feedback_id)
        return item.to_dict() if item else None

    def list_feedback(
        self,
        category: Optional[FeedbackCategory] = None,
        priority: Optional[FeedbackPriority] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        items = list(self._store.values())
        if category:
            items = [i for i in items if i.feedback_type == category]
        if priority:
            items = [i for i in items if i.priority == priority]
        return [i.to_dict() for i in sorted(items, key=lambda x: x.created_at, reverse=True)[:limit]]

    def generate_feedback_analytics(self) -> Dict[str, Any]:
        """Aggregate feedback analytics: volume, category distribution, priority distribution."""
        total = len(self._store)
        if total == 0:
            return {
                "total_feedback": 0,
                "category_breakdown": {},
                "priority_breakdown": {},
                "top_issues": [],
                "critical_unresolved_count": 0,
            }

        category_counts: Dict[str, int] = {}
        priority_counts: Dict[str, int] = {}
        critical_unresolved = 0

        for item in self._store.values():
            cat = item.feedback_type.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

            prio = item.priority.value
            priority_counts[prio] = priority_counts.get(prio, 0) + 1

            if item.priority == FeedbackPriority.CRITICAL and not item.resolved:
                critical_unresolved += 1

        top_issues = [
            {"feedback_id": i.feedback_id, "type": i.feedback_type.value, "priority": i.priority.value, "desc": i.description[:60]}
            for i in sorted(self._store.values(), key=lambda x: (x.priority == FeedbackPriority.CRITICAL, x.created_at), reverse=True)[:5]
        ]

        return {
            "total_feedback": total,
            "category_breakdown": category_counts,
            "priority_breakdown": priority_counts,
            "top_issues": top_issues,
            "critical_unresolved_count": critical_unresolved,
        }

    def clear(self) -> None:
        self._store.clear()


feedback_intelligence = UserFeedbackIntelligence()
