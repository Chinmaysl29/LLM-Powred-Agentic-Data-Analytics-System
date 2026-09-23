"""
Phase 13.8 — Customer Success Platform
Empowers customer onboarding checklists, self-service Knowledge Base search,
SLA-backed enterprise support ticketing, and customer satisfaction feedback (CSAT/NPS).
"""

from typing import Dict, Any, List, Optional
import time
import uuid
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.operations.customer_success")


class SupportTicket(BaseModel):
    ticket_id: str = Field(default_factory=lambda: f"tkt-{uuid.uuid4().hex[:6]}")
    tenant_id: str
    user_email: str
    subject: str
    description: str
    priority: str = "NORMAL" # "LOW", "NORMAL", "HIGH", "URGENT"
    status: str = "OPEN"     # "OPEN", "IN_PROGRESS", "RESOLVED"
    responses: List[Dict[str, str]] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class CustomerSuccessPlatform:
    """
    Manages tenant onboarding flows, technical support desk, and customer sentiment.
    """

    def __init__(self):
        self._onboarding_state: Dict[str, Dict[str, bool]] = {}
        self._kb_articles: List[Dict[str, Any]] = [
            {"id": "kb-1", "title": "Connecting Snowflake via OAuth", "category": "connectors", "content": "How to set up enterprise warehouse connection."},
            {"id": "kb-2", "title": "Configuring Prophet Forecast Tournaments", "category": "forecasting", "content": "Best practices for daily retail demand forecasting."},
            {"id": "kb-3", "title": "Setting up Slack Block Kit Alerts", "category": "integrations", "content": "Automating KPI anomaly delivery into executive channels."}
        ]
        self._tickets: Dict[str, SupportTicket] = {}
        self._nps_feedback: List[Dict[str, Any]] = []

    # Onboarding
    def init_onboarding(self, tenant_id: str) -> Dict[str, bool]:
        steps = {
            "connect_first_dataset": False,
            "run_first_eda": False,
            "invite_team_members": False,
            "setup_notifications": False
        }
        self._onboarding_state[tenant_id] = steps
        return steps

    def complete_onboarding_step(self, tenant_id: str, step_name: str) -> Dict[str, Any]:
        if tenant_id not in self._onboarding_state:
            self.init_onboarding(tenant_id)
        steps = self._onboarding_state[tenant_id]
        if step_name in steps:
            steps[step_name] = True
        completed = sum(1 for v in steps.values() if v)
        return {
            "tenant_id": tenant_id,
            "step_completed": step_name,
            "progress_percentage": round((completed / len(steps)) * 100.0, 1),
            "all_complete": completed == len(steps)
        }

    # Knowledge Base
    def search_kb(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        return [a for a in self._kb_articles if q in a["title"].lower() or q in a["content"].lower()]

    # Support Tickets
    def create_support_ticket(
        self,
        tenant_id: str,
        user_email: str,
        subject: str,
        description: str,
        priority: str = "NORMAL"
    ) -> SupportTicket:
        ticket = SupportTicket(
            tenant_id=tenant_id,
            user_email=user_email,
            subject=subject,
            description=description,
            priority=priority
        )
        self._tickets[ticket.ticket_id] = ticket
        logger.info("Created support ticket %s: '%s'", ticket.ticket_id, subject)
        return ticket

    def reply_ticket(self, ticket_id: str, author: str, text: str) -> bool:
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False
        ticket.responses.append({"author": author, "text": text, "time": str(time.time())})
        ticket.status = "IN_PROGRESS"
        return True

    def resolve_ticket(self, ticket_id: str) -> bool:
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return False
        ticket.status = "RESOLVED"
        return True

    # Feedback (CSAT & NPS)
    def submit_nps_survey(self, tenant_id: str, score: int, comment: str = "") -> Dict[str, Any]:
        """Record NPS score (0 to 10)."""
        entry = {
            "tenant_id": tenant_id,
            "score": score,
            "category": "PROMOTER" if score >= 9 else ("PASSIVE" if score >= 7 else "DETRACTOR"),
            "comment": comment,
            "submitted_at": time.time()
        }
        self._nps_feedback.append(entry)
        return entry
