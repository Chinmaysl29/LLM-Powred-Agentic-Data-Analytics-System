"""Phase 12.5.9 — Enterprise Agent Router.

Performs natural language intent detection, domain classification, intelligent
agent routing, fallback handling, and multi-agent collaborative coordination.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set

from backend.domain_agents.base import BaseDomainAgent, DomainAnalysisResult
from backend.domain_agents.executive import ExecutiveAgent
from backend.domain_agents.finance import FinanceAgent
from backend.domain_agents.hr import HRAgent
from backend.domain_agents.marketing import MarketingAgent
from backend.domain_agents.risk import RiskAgent
from backend.domain_agents.sales import SalesAgent
from backend.domain_agents.supply_chain import SupplyChainAgent

logger = logging.getLogger(__name__)

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "finance": [
        "revenue", "profit", "cogs", "opex", "margin", "cash", "runway", "budget", "ebitda", "cfo", "financial"
    ],
    "sales": [
        "lead", "pipeline", "deal", "quota", "win rate", "opportunity", "conversion", "sales", "prospect"
    ],
    "marketing": [
        "campaign", "cac", "roas", "ad spend", "retention", "channel", "marketing", "acquisition", "impressions"
    ],
    "hr": [
        "headcount", "attrition", "hiring", "turnover", "enps", "employee", "workforce", "salary", "compensation"
    ],
    "supply_chain": [
        "inventory", "sku", "stockout", "supplier", "lead time", "warehouse", "logistics", "supply chain", "reorder"
    ],
    "risk": [
        "risk", "compliance", "fraud", "audit", "governance", "exposure", "vulnerability", "gdpr", "soc2"
    ],
    "executive": [
        "executive", "board", "summary", "overview", "strategic", "ceo", "kpi", "scorecard", "company performance"
    ],
}


class EnterpriseAgentRouter:
    """Intelligent dispatcher matching queries to specialized domain agents."""

    def __init__(self) -> None:
        self.agents: Dict[str, BaseDomainAgent] = {
            "finance": FinanceAgent(),
            "sales": SalesAgent(),
            "marketing": MarketingAgent(),
            "hr": HRAgent(),
            "supply_chain": SupplyChainAgent(),
            "risk": RiskAgent(),
            "executive": ExecutiveAgent(),
        }

    def classify_domains(self, query: str) -> List[str]:
        """Classify which business domains are referenced in the user request."""
        clean_query = query.lower()
        matched_scores: Dict[str, int] = {d: 0 for d in self.agents}

        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", clean_query):
                    matched_scores[domain] += 1

        # Extract domains with at least 1 match, sorted by relevance
        matched = [d for d, count in matched_scores.items() if count > 0]
        matched.sort(key=lambda d: matched_scores[d], reverse=True)

        if not matched:
            return ["executive"]  # Default fallback
        return matched

    def route_single(
        self,
        query: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> DomainAnalysisResult:
        """Route to the primary matching domain agent."""
        domains = self.classify_domains(query)
        target_domain = domains[0]
        agent = self.agents.get(target_domain, self.agents["executive"])

        logger.info("Routing query '%s' -> [%s]", query[:50], agent.name)
        return agent.analyze(data, context=context)

    def route_multi(
        self,
        query: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> DomainAnalysisResult:
        """Coordinate multiple specialized domain agents and synthesize via ExecutiveAgent."""
        domains = self.classify_domains(query)

        # If only one domain or only executive, route directly
        if len(domains) == 1 and domains[0] != "executive":
            return self.agents[domains[0]].analyze(data, context=context)

        # Multi-agent execution: collect sub-domain outputs
        sub_results: Dict[str, Any] = {}
        for d in domains:
            if d != "executive" and d in self.agents:
                res = self.agents[d].analyze(data.get(d, data), context=context)
                sub_results[d] = res.kpis

        # Feed sub-results into ExecutiveAgent for master briefing
        exec_agent = self.agents["executive"]
        return exec_agent.analyze(sub_results, context=context)
