"""Phase 12.5 — Advanced Agent Ecosystem Package.

Exports BaseDomainAgent, all 7 domain agents (Finance, Sales, Marketing, HR,
Supply Chain, Risk, Executive), EnterpriseAgentRouter, and AgentEvaluator.
"""

from backend.domain_agents.base import (
    BaseDomainAgent,
    DomainAnalysisResult,
    DomainInsight,
    DomainRecommendation,
    DomainRisk,
    DomainSeverity,
)
from backend.domain_agents.evaluator import AgentEvaluator, AgentScorecard
from backend.domain_agents.executive import ExecutiveAgent
from backend.domain_agents.finance import FinanceAgent
from backend.domain_agents.hr import HRAgent
from backend.domain_agents.marketing import MarketingAgent
from backend.domain_agents.risk import RiskAgent
from backend.domain_agents.router import EnterpriseAgentRouter
from backend.domain_agents.sales import SalesAgent
from backend.domain_agents.supply_chain import SupplyChainAgent

__all__ = [
    "BaseDomainAgent",
    "DomainSeverity",
    "DomainInsight",
    "DomainRisk",
    "DomainRecommendation",
    "DomainAnalysisResult",
    "FinanceAgent",
    "SalesAgent",
    "MarketingAgent",
    "HRAgent",
    "SupplyChainAgent",
    "RiskAgent",
    "ExecutiveAgent",
    "EnterpriseAgentRouter",
    "AgentEvaluator",
    "AgentScorecard",
]
