"""Phase 7 — Recommendation & Decision Intelligence Schemas.

Defines Pydantic v2 schemas for all Phase 7 modules:
- Foundation & Scoring (7.1)
- Business Recommendations (7.2)
- Cost Optimization (7.3)
- Revenue Optimization (7.4)
- Pricing Intelligence (7.5)
- Marketing Intelligence (7.6)
- Inventory Optimization (7.7)
- Action Prioritization (7.8)
- Decision Support Agent (7.9)
- End-to-End Recommendation Pipeline (7.10)
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class OpportunityType(str, Enum):
    """Core categories of analytical opportunities."""

    GROWTH = "growth"
    REVENUE = "revenue"
    COST_REDUCTION = "cost_reduction"
    RISK_REDUCTION = "risk_reduction"


class PriorityLevel(str, Enum):
    """Standardized action priority tiers."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RecommendationCategory(str, Enum):
    """Business domain category for recommendations."""

    GROWTH = "growth"
    OPERATIONAL = "operational"
    RISK_MITIGATION = "risk_mitigation"
    EXPANSION = "expansion"
    COST_OPTIMIZATION = "cost_optimization"
    REVENUE_OPTIMIZATION = "revenue_optimization"
    PRICING = "pricing"
    MARKETING = "marketing"
    INVENTORY = "inventory"
    GENERAL = "general"


class ScoringWeights(BaseModel):
    """Configurable weights for scoring calculations."""

    model_config = ConfigDict(extra="ignore")

    impact_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    confidence_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    urgency_weight: float = Field(default=0.0, ge=0.0, le=1.0)


class AnalyticalInputs(BaseModel):
    """Unified container aggregating upstream analytical outputs."""

    model_config = ConfigDict(extra="ignore")

    eda_results: dict[str, Any] | None = Field(
        default=None, description="Exploratory Data Analysis metrics and patterns"
    )
    statistics_results: dict[str, Any] | None = Field(
        default=None, description="Descriptive and inferential statistical findings"
    )
    forecast_results: dict[str, Any] | None = Field(
        default=None, description="Time-series predictions and confidence bands"
    )
    validation_results: dict[str, Any] | None = Field(
        default=None, description="Forecast validation status, MAPE, and gates"
    )
    rag_results: dict[str, Any] | None = Field(
        default=None, description="Knowledge base context and business domain notes"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary execution or dataset metadata"
    )


class RecommendationItem(BaseModel):
    """Canonical recommendation model with standardized impact and confidence scoring."""

    model_config = ConfigDict(extra="ignore")

    opportunity: str = Field(..., description="Actionable opportunity statement")
    impact_score: float = Field(
        ..., ge=0.0, le=100.0, description="Estimated business magnitude (0 to 100)"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=100.0, description="Statistical / analytical confidence (0 to 100)"
    )
    priority: PriorityLevel = Field(
        ..., description="Calculated action priority: Critical, High, Medium, or Low"
    )
    category: RecommendationCategory = Field(
        default=RecommendationCategory.GENERAL, description="Recommendation category"
    )
    action_plan: str = Field(
        default="", description="Prescriptive action steps to capitalize on opportunity"
    )
    estimated_value: float = Field(
        default=0.0, description="Estimated dollar or financial impact if realized"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Supporting metrics, evidence, and rationale"
    )


class FoundationRecommendationOutput(BaseModel):
    """Phase 7.1 output contract."""

    model_config = ConfigDict(extra="ignore")

    opportunity: str = Field(..., description="Primary detected opportunity")
    impact_score: float = Field(..., ge=0.0, le=100.0, description="Impact score 0-100")
    confidence_score: float = Field(
        ..., ge=0.0, le=100.0, description="Confidence score 0-100"
    )
    priority: str = Field(..., description="Priority tier string")
    detected_opportunities: list[dict[str, Any]] = Field(
        default_factory=list, description="All detected opportunity items"
    )


class BusinessRecommendationsOutput(BaseModel):
    """Phase 7.2 output contract."""

    model_config = ConfigDict(extra="ignore")

    recommendations: list[dict[str, Any]] = Field(
        default_factory=list, description="Ranked business recommendations"
    )


class CostOptimizationOutput(BaseModel):
    """Phase 7.3 output contract."""

    model_config = ConfigDict(extra="ignore")

    cost_savings: list[dict[str, Any]] = Field(
        default_factory=list, description="Cost saving opportunities identified"
    )
    estimated_savings: float = Field(
        default=0.0, description="Total projected dollar or percentage savings"
    )


class RevenueOptimizationOutput(BaseModel):
    """Phase 7.4 output contract."""

    model_config = ConfigDict(extra="ignore")

    opportunities: list[dict[str, Any]] = Field(
        default_factory=list, description="Upsell, cross-sell, and growth opportunities"
    )
    estimated_revenue_increase: float = Field(
        default=0.0, description="Total projected revenue expansion"
    )


class PricingIntelligenceOutput(BaseModel):
    """Phase 7.5 output contract."""

    model_config = ConfigDict(extra="ignore")

    pricing_actions: list[dict[str, Any]] = Field(
        default_factory=list, description="Recommended price adjustments and elasticity notes"
    )
    expected_impact: float = Field(
        default=0.0, description="Expected financial impact from pricing changes"
    )


class MarketingIntelligenceOutput(BaseModel):
    """Phase 7.6 output contract."""

    model_config = ConfigDict(extra="ignore")

    marketing_actions: list[dict[str, Any]] = Field(
        default_factory=list, description="Campaign optimizations and budget reallocation"
    )
    expected_roi: float = Field(
        default=0.0, description="Projected ROI / ROAS multiplier or percentage"
    )


class InventoryOptimizationOutput(BaseModel):
    """Phase 7.7 output contract."""

    model_config = ConfigDict(extra="ignore")

    inventory_actions: list[dict[str, Any]] = Field(
        default_factory=list, description="Reorder and destocking actions"
    )
    expected_inventory_savings: float = Field(
        default=0.0, description="Projected inventory holding or stockout savings"
    )


class ActionPrioritizationOutput(BaseModel):
    """Phase 7.8 output contract."""

    model_config = ConfigDict(extra="ignore")

    prioritized_actions: list[dict[str, Any]] = Field(
        default_factory=list, description="Actions sorted and grouped by priority"
    )


class DecisionSupportOutput(BaseModel):
    """Phase 7.9 output contract."""

    model_config = ConfigDict(extra="ignore")

    decision_summary: str = Field(..., description="Executive briefing and decision memo")
    recommended_action: str = Field(
        ..., description="Top recommended strategic action"
    )
    risk_assessment: str = Field(
        default="", description="Evaluation of downside risks and caveats"
    )
    strategic_priorities: list[str] = Field(
        default_factory=list, description="Core execution milestones"
    )


class RecommendationPipelineOutput(BaseModel):
    """Phase 7.10 output contract."""

    model_config = ConfigDict(extra="ignore")

    recommendations: list[dict[str, Any]] = Field(
        default_factory=list, description="All aggregated recommendations"
    )
    prioritized_actions: list[dict[str, Any]] = Field(
        default_factory=list, description="Ranked and prioritized action list"
    )
    decision_summary: str = Field(..., description="Executive decision overview")
    business_impact: str = Field(..., description="Projected bottom-line impact assessment")
    module_details: dict[str, Any] = Field(
        default_factory=dict, description="Granular outputs from individual engines"
    )
