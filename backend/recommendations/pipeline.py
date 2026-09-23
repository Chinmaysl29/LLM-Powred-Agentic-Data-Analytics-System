"""Phase 7.10 — End-to-End Recommendation Pipeline.

Orchestrates all Phase 7 intelligence engines:
1. Recommendation Foundation (7.1)
2. Business Recommendation Engine (7.2)
3. Cost Optimization Engine (7.3)
4. Revenue Optimization Engine (7.4)
5. Pricing Intelligence Engine (7.5)
6. Marketing Intelligence Engine (7.6)
7. Inventory Optimization Engine (7.7)
8. Action Prioritization Engine (7.8)
9. Decision Support Agent (7.9)
"""

import logging
from typing import Any

from backend.agents.recommendation_agent import DecisionSupportAgent
from backend.app.schemas.recommendations import (
    AnalyticalInputs,
    RecommendationPipelineOutput,
)
from backend.recommendations.action_prioritization import ActionPrioritizationEngine
from backend.recommendations.business_recommendations import BusinessRecommendationEngine
from backend.recommendations.cost_optimization import CostOptimizationEngine
from backend.recommendations.foundation import RecommendationFoundation
from backend.recommendations.inventory_recommendations import InventoryOptimizationEngine
from backend.recommendations.marketing_recommendations import MarketingIntelligenceEngine
from backend.recommendations.pricing_recommendations import PricingIntelligenceEngine
from backend.recommendations.revenue_optimization import RevenueOptimizationEngine

logger = logging.getLogger(__name__)


class RecommendationPipeline:
    """Master orchestrator integrating all recommendation, optimization, and decision engines."""

    def __init__(
        self,
        foundation: RecommendationFoundation | None = None,
        business_engine: BusinessRecommendationEngine | None = None,
        cost_engine: CostOptimizationEngine | None = None,
        revenue_engine: RevenueOptimizationEngine | None = None,
        pricing_engine: PricingIntelligenceEngine | None = None,
        marketing_engine: MarketingIntelligenceEngine | None = None,
        inventory_engine: InventoryOptimizationEngine | None = None,
        prioritization_engine: ActionPrioritizationEngine | None = None,
        decision_agent: DecisionSupportAgent | None = None,
    ) -> None:
        self.foundation = foundation or RecommendationFoundation()
        self.business_engine = business_engine or BusinessRecommendationEngine(foundation=self.foundation)
        self.cost_engine = cost_engine or CostOptimizationEngine(foundation=self.foundation)
        self.revenue_engine = revenue_engine or RevenueOptimizationEngine(foundation=self.foundation)
        self.pricing_engine = pricing_engine or PricingIntelligenceEngine(foundation=self.foundation)
        self.marketing_engine = marketing_engine or MarketingIntelligenceEngine(foundation=self.foundation)
        self.inventory_engine = inventory_engine or InventoryOptimizationEngine(foundation=self.foundation)
        self.prioritization_engine = prioritization_engine or ActionPrioritizationEngine()
        self.decision_agent = decision_agent or DecisionSupportAgent(foundation=self.foundation)

    def execute_pipeline(
        self,
        inputs: dict[str, Any] | AnalyticalInputs,
        require_forecast: bool = True,
    ) -> RecommendationPipelineOutput:
        """Execute the full end-to-end recommendation workflow."""
        logger.info("Initiating full Phase 7 Recommendation Pipeline execution")

        # 1. Foundation Validation and Opportunity Discovery
        validated_inputs = self.foundation.validate_inputs(inputs, require_forecast=require_forecast)
        raw_dict = validated_inputs.model_dump()

        # Merge top-level or eda/forecast inputs for sub-engines
        merged_context: dict[str, Any] = {**raw_dict}
        if validated_inputs.forecast_results:
            merged_context.update(validated_inputs.forecast_results)
        if validated_inputs.eda_results:
            merged_context.update(validated_inputs.eda_results)
        if validated_inputs.statistics_results:
            merged_context.update(validated_inputs.statistics_results)

        # 2. Execute Sub-Engines
        logger.debug("Executing intelligence engines across modules")

        # 7.1 Foundation Opportunities
        foundation_items = self.foundation.detect_opportunities(validated_inputs)

        # 7.2 Business Recommendations
        biz_output = self.business_engine.generate_recommendations(merged_context)

        # 7.3 Cost Optimization
        cost_output = self.cost_engine.analyze_costs(merged_context)

        # 7.4 Revenue Optimization
        rev_output = self.revenue_engine.analyze_revenue(merged_context)

        # 7.5 Pricing Intelligence
        pricing_output = self.pricing_engine.analyze_pricing(merged_context)

        # 7.6 Marketing Intelligence
        # Adapt marketing inputs from merged_context
        marketing_input: dict[str, Any] = {}
        if "marketing_roi" in merged_context:
            marketing_input["roi"] = merged_context["marketing_roi"]
        if "marketing_spend" in merged_context:
            marketing_input["spend"] = merged_context["marketing_spend"]
        if "campaigns" in merged_context:
            marketing_input["campaigns"] = merged_context["campaigns"]
        if not marketing_input:
            marketing_input = merged_context
        marketing_output = self.marketing_engine.analyze_campaigns(marketing_input)

        # 7.7 Inventory Optimization
        inv_input: dict[str, Any] = {}
        if "inventory_overstock_pct" in merged_context:
            overstock = float(merged_context["inventory_overstock_pct"])
            inv_input["current_stock"] = 1000.0 * (1.0 + overstock)
            inv_input["forecasted_demand"] = 1000.0
        elif "current_stock" in merged_context and "forecasted_demand" in merged_context:
            inv_input = merged_context
        else:
            inv_input = merged_context
        inv_output = self.inventory_engine.analyze_inventory(inv_input)

        # 3. Master Recommendation Aggregation
        all_recommendations: list[dict[str, Any]] = []

        # From Foundation
        for f_item in foundation_items:
            all_recommendations.append(f_item.model_dump())

        # From Business Recommendations
        for b_item in biz_output.recommendations:
            all_recommendations.append(b_item)

        # From Cost Optimization
        for c_item in cost_output.cost_savings:
            if c_item.get("estimated_savings", 0) > 0:
                all_recommendations.append({
                    "opportunity": c_item.get("recommendation", c_item["area"]),
                    "impact_score": 75.0,
                    "confidence_score": 85.0,
                    "estimated_value": c_item.get("estimated_savings", 0.0),
                    "priority": c_item.get("priority", "High"),
                    "category": "cost_optimization",
                    "details": c_item,
                })

        # From Revenue Optimization
        for r_item in rev_output.opportunities:
            if r_item.get("estimated_revenue_increase", 0) > 0:
                all_recommendations.append({
                    "opportunity": r_item["opportunity"],
                    "impact_score": 85.0,
                    "confidence_score": 80.0,
                    "estimated_value": r_item.get("estimated_revenue_increase", 0.0),
                    "priority": r_item.get("priority", "High"),
                    "category": "revenue_optimization",
                    "details": r_item,
                })

        # From Pricing Intelligence
        for p_item in pricing_output.pricing_actions:
            all_recommendations.append({
                "opportunity": p_item["action"],
                "impact_score": 70.0,
                "confidence_score": 80.0,
                "estimated_value": p_item.get("expected_impact", 0.0),
                "priority": p_item.get("priority", "Medium"),
                "category": "pricing",
                "details": p_item,
            })

        # From Marketing Intelligence
        for m_item in marketing_output.marketing_actions:
            all_recommendations.append({
                "opportunity": m_item["recommendation"],
                "impact_score": 75.0,
                "confidence_score": 85.0,
                "estimated_value": m_item.get("projected_gain", 0.0),
                "priority": m_item.get("priority", "High"),
                "category": "marketing",
                "details": m_item,
            })

        # From Inventory Optimization
        for i_item in inv_output.inventory_actions:
            all_recommendations.append({
                "opportunity": i_item["recommendation"],
                "impact_score": 70.0,
                "confidence_score": 90.0,
                "estimated_value": i_item.get("expected_savings", 0.0),
                "priority": i_item.get("priority", "Medium"),
                "category": "inventory",
                "details": i_item,
            })

        # 4. Action Prioritization (7.8)
        prioritization_output = self.prioritization_engine.prioritize_actions(all_recommendations)
        prioritized_actions = prioritization_output.prioritized_actions

        # 5. Decision Support Agent (7.9)
        decision_context = {
            **merged_context,
            "recommendations": prioritized_actions[:5],
        }
        decision_guidance = self.decision_agent.generate_decision_guidance(decision_context)

        # 6. Quantified Business Impact Assessment
        total_savings = (
            cost_output.estimated_savings + inv_output.expected_inventory_savings
        )
        total_growth = (
            rev_output.estimated_revenue_increase + max(pricing_output.expected_impact, 0.0)
        )
        net_financial_benefit = total_savings + total_growth

        critical_count = sum(1 for a in prioritized_actions if a.get("priority") == "Critical")
        high_count = sum(1 for a in prioritized_actions if a.get("priority") == "High")

        impact_statement = (
            f"Quantified Enterprise Business Impact: ${net_financial_benefit:+,.2f} net projected upside. "
            f"Includes ${total_savings:,.2f} in identified operational & inventory cost reductions and "
            f"${total_growth:,.2f} in revenue/pricing expansion opportunities. "
            f"{critical_count} Critical and {high_count} High priority interventions ready for execution."
        )

        logger.info(
            "Recommendation Pipeline complete. Identified %d prioritized actions with %s",
            len(prioritized_actions),
            impact_statement,
        )

        return RecommendationPipelineOutput(
            recommendations=all_recommendations,
            prioritized_actions=prioritized_actions,
            decision_summary=decision_guidance.decision_summary,
            business_impact=impact_statement,
            module_details={
                "cost_optimization": cost_output.model_dump(),
                "revenue_optimization": rev_output.model_dump(),
                "pricing_intelligence": pricing_output.model_dump(),
                "marketing_intelligence": marketing_output.model_dump(),
                "inventory_optimization": inv_output.model_dump(),
            },
        )
