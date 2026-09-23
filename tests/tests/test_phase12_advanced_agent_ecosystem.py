"""Phase 12.5 — Advanced Agent Ecosystem Integration Tests.

Validates:
1. 12.5.1 Domain Agent Framework (Initialization, execution, contract validation)
2. 12.5.2 Finance Agent (Revenue, margins, cost, cash runway, recommendations)
3. 12.5.3 Sales Agent (Pipeline velocity, conversion rates, regional attainment)
4. 12.5.4 Marketing Agent (Campaigns, ROAS/ROI, CAC, retention)
5. 12.5.5 HR Agent (Workforce metrics, attrition, hiring velocity)
6. 12.5.6 Supply Chain Agent (Inventory turns, stockout risk, supplier scoring)
7. 12.5.7 Risk Agent (Composite risk scoring, operational/compliance detection)
8. 12.5.8 Executive Agent (KPI consolidation, executive briefing, board directives)
9. 12.5.9 Enterprise Agent Router (Domain intent classification, single & multi-agent routing)
10. 12.5.10 Agent Evaluation Framework & Performance Certification
"""

import json

import pytest

from backend.domain_agents.base import (
    BaseDomainAgent,
    DomainAnalysisResult,
    DomainInsight,
    DomainSeverity,
)
from backend.domain_agents.evaluator import AgentEvaluator
from backend.domain_agents.executive import ExecutiveAgent
from backend.domain_agents.finance import FinanceAgent
from backend.domain_agents.hr import HRAgent
from backend.domain_agents.marketing import MarketingAgent
from backend.domain_agents.risk import RiskAgent
from backend.domain_agents.router import EnterpriseAgentRouter
from backend.domain_agents.sales import SalesAgent
from backend.domain_agents.supply_chain import SupplyChainAgent


# ---------------------------------------------------------------------------
# 12.5.1 Domain Agent Framework
# ---------------------------------------------------------------------------
def test_domain_agent_framework():
    """Verify BaseDomainAgent contracts, initialization, execution, and validation."""
    agent = FinanceAgent()
    assert agent.name == "FinanceAgent"
    assert agent.domain == "finance"

    result = agent.analyze({"revenue": 500_000, "cogs": 200_000, "opex": 150_000})
    assert isinstance(result, DomainAnalysisResult)
    assert agent.validate_results(result) is True
    assert len(result.insights) >= 1
    assert len(result.recommendations) >= 1
    assert result.execution_time_ms >= 0

    # Serialization check
    res_dict = result.to_dict()
    assert res_dict["agent_name"] == "FinanceAgent"
    assert res_dict["domain"] == "finance"


# ---------------------------------------------------------------------------
# 12.5.2 Finance Agent
# ---------------------------------------------------------------------------
def test_finance_agent():
    """Test revenue, margin, cost, runway, and risk detection."""
    agent = FinanceAgent()
    payload = {
        "revenue": 2_000_000.0,
        "cogs": 800_000.0,
        "opex": 700_000.0,
        "budget_target": 1_800_000.0,
        "cash_reserves": 5_000_000.0,
    }
    result = agent.analyze(payload)

    assert result.kpis["gross_profit"] == 1_200_000.0
    assert result.kpis["net_profit"] == 500_000.0
    assert result.kpis["gross_margin_pct"] == 60.0
    assert result.kpis["net_margin_pct"] == 25.0
    assert result.kpis["budget_variance_pct"] > 0

    assert "Revenue Over-Performance" in [i.title for i in result.insights]
    assert len(result.recommendations) >= 1


# ---------------------------------------------------------------------------
# 12.5.3 Sales Agent
# ---------------------------------------------------------------------------
def test_sales_agent():
    """Test pipeline, lead conversion, quota attainment, and sales forecasting."""
    agent = SalesAgent()
    payload = {
        "total_leads": 2000,
        "qualified_leads": 600,
        "closed_won": 180,
        "pipeline_value": 5_000_000.0,
        "won_deal_value": 1_500_000.0,
        "sales_quota": 1_200_000.0,
    }
    result = agent.analyze(payload)

    assert result.kpis["lead_to_opp_pct"] == 30.0
    assert result.kpis["opp_win_rate_pct"] == 30.0
    assert result.kpis["quota_attainment_pct"] == 125.0
    assert result.kpis["average_deal_size"] > 0

    assert "Quota Attainment Exceeded" in [i.title for i in result.insights]


# ---------------------------------------------------------------------------
# 12.5.4 Marketing Agent
# ---------------------------------------------------------------------------
def test_marketing_agent():
    """Test campaign ROAS, CAC, ROI, and customer retention."""
    agent = MarketingAgent()
    payload = {
        "total_ad_spend": 100_000.0,
        "attributed_revenue": 500_000.0,
        "new_customers": 1000,
        "retention_90d_pct": 85.0,
    }
    result = agent.analyze(payload)

    assert result.kpis["roas"] == 5.0
    assert result.kpis["cac"] == 100.0
    assert result.kpis["net_marketing_roi_pct"] == 400.0

    assert "Strong Blended ROAS" in [i.title for i in result.insights]


# ---------------------------------------------------------------------------
# 12.5.5 HR Agent
# ---------------------------------------------------------------------------
def test_hr_agent():
    """Test headcount, turnover/attrition, time-to-hire, and sentiment."""
    agent = HRAgent()
    payload = {
        "total_headcount": 500,
        "departures_annualized": 40,
        "open_requisitions": 35,
        "avg_time_to_hire_days": 32.0,
        "enps": 52.0,
    }
    result = agent.analyze(payload)

    assert result.kpis["attrition_rate_pct"] == 8.0
    assert result.kpis["total_headcount"] == 500
    assert result.kpis["enps"] == 52.0
    assert "Annualized Attrition Within Target" in [i.title for i in result.insights]


# ---------------------------------------------------------------------------
# 12.5.6 Supply Chain Agent
# ---------------------------------------------------------------------------
def test_supply_chain_agent():
    """Test inventory turns, stockout risk, and supplier performance."""
    agent = SupplyChainAgent()
    payload = {
        "total_skus": 5000,
        "inventory_value": 2_500_000.0,
        "cogs_annual": 15_000_000.0,
        "stockout_skus": 15,
        "supplier_on_time_pct": 96.5,
    }
    result = agent.analyze(payload)

    assert result.kpis["inventory_turns"] == 6.0
    assert result.kpis["stockout_rate_pct"] == 0.3
    assert result.kpis["supplier_on_time_pct"] == 96.5


# ---------------------------------------------------------------------------
# 12.5.7 Risk Agent
# ---------------------------------------------------------------------------
def test_risk_agent():
    """Test composite risk index and risk categorization."""
    agent = RiskAgent()
    payload = {
        "operational_risk": 20.0,
        "financial_risk": 15.0,
        "data_quality_risk": 10.0,
        "forecast_risk": 18.0,
        "compliance_risk": 12.0,
    }
    result = agent.analyze(payload)

    assert result.kpis["composite_risk_score"] < 30.0
    assert result.kpis["risk_tier"] == "LOW"
    assert "Enterprise Composite Risk Posture" in [i.title for i in result.insights]


# ---------------------------------------------------------------------------
# 12.5.8 Executive Agent
# ---------------------------------------------------------------------------
def test_executive_agent():
    """Test cross-agent consolidation, KPI synthesis, and board briefing."""
    agent = ExecutiveAgent()
    payload = {
        "finance": {"revenue": 2_500_000.0, "net_profit": 600_000.0},
        "sales": {"quota_attainment_pct": 118.0},
        "marketing": {"roas": 4.5},
        "hr": {"total_headcount": 520},
        "risk": {"composite_risk_score": 18.5},
    }
    result = agent.analyze(payload)

    assert result.kpis["topline_revenue"] == 2_500_000.0
    assert result.kpis["executive_health_grade"] == "A+"
    assert "BOARD EXECUTIVE BRIEFING" in result.summary


# ---------------------------------------------------------------------------
# 12.5.9 Enterprise Agent Router
# ---------------------------------------------------------------------------
def test_agent_router():
    """Verify domain classification, single routing, and multi-agent coordination."""
    router = EnterpriseAgentRouter()

    # 1. Classification
    assert "finance" in router.classify_domains("What is our Q3 revenue and gross profit margin?")
    assert "sales" in router.classify_domains("Show me sales pipeline conversion and quota attainment")
    assert "marketing" in router.classify_domains("Analyze campaign ROAS and customer acquisition costs")
    assert "hr" in router.classify_domains("Check employee headcount and turnover attrition rates")

    # 2. Single Domain Route
    fin_res = router.route_single("Analyze our revenue and cash burn", {"revenue": 1_000_000})
    assert fin_res.domain == "finance"

    sales_res = router.route_single("Review our sales pipeline deals", {"pipeline_value": 2_000_000})
    assert sales_res.domain == "sales"

    # 3. Multi-Agent Route (Cross-Domain)
    multi_res = router.route_multi(
        "Give me a consolidated briefing on sales quota, marketing spend, and financial profit",
        {
            "finance": {"revenue": 1_500_000, "net_profit": 350_000},
            "sales": {"quota_attainment_pct": 110},
            "marketing": {"roas": 4.2},
        },
    )
    assert multi_res.domain == "executive"
    assert multi_res.kpis["topline_revenue"] == 1_500_000


# ---------------------------------------------------------------------------
# 12.5.10 Agent Evaluation Framework & Performance Certification
# ---------------------------------------------------------------------------
def test_agent_evaluation_framework():
    """Verify evaluator metrics across all 7 domain agents and confirm certification report."""
    evaluator = AgentEvaluator()

    # Individual scorecard evaluation
    fin_card = evaluator.evaluate_agent("finance_agent")
    assert fin_card.accuracy_score >= 90.0
    assert fin_card.composite_rating == 95

    # Full performance report certification
    report = evaluator.generate_performance_report()

    expected_ratings = {
        "finance_agent": 95,
        "sales_agent": 93,
        "marketing_agent": 94,
        "hr_agent": 92,
        "supply_chain_agent": 91,
        "risk_agent": 96,
        "executive_agent": 97,
    }

    assert report == expected_ratings

    # Confirm strict JSON formatting compliance
    report_json = json.dumps(report, indent=2)
    parsed = json.loads(report_json)
    assert parsed["finance_agent"] == 95
    assert parsed["sales_agent"] == 93
    assert parsed["marketing_agent"] == 94
    assert parsed["hr_agent"] == 92
    assert parsed["supply_chain_agent"] == 91
    assert parsed["risk_agent"] == 96
    assert parsed["executive_agent"] == 97
