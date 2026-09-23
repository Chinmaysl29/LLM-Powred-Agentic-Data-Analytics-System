"""Pydantic schemas for Phase 3.8 Executive Summary Agent.

Provides data models for executive summaries, multi-level business narratives,
key findings, opportunity and risk detection, action horizons, business health scoring,
and priority classifications.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


SummaryLevel = Literal["quick", "manager", "executive", "board"]
PriorityLevel = Literal["critical", "high", "medium", "low"]
ActionTimeframe = Literal["immediate", "short_term", "long_term"]


class PriorityItem(BaseModel):
    """Classified high-signal finding, opportunity, risk, or action."""

    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., description="Short summary headline")
    priority: PriorityLevel = Field(..., description="Classification: critical, high, medium, low")
    category: str = Field(..., description="Category: finding, opportunity, risk, action")
    description: str = Field(..., description="Actionable or analytical detail")
    impact: str | None = Field(None, description="Estimated business or metric impact")


class ActionItem(BaseModel):
    """Prioritized business action mapped to a time horizon."""

    timeframe: ActionTimeframe = Field(..., description="Horizon: immediate, short_term, long_term")
    action: str = Field(..., description="Actionable recommendation")
    rationale: str | None = Field(None, description="Analytical grounding or driver")
    priority: PriorityLevel = Field(default="medium", description="Priority tier")


class MultiLevelSummaries(BaseModel):
    """Multi-tier summaries tailored to different organizational audiences."""

    level_1_quick_summary: str = Field(..., description="30-second elevator pitch / headline narrative")
    level_2_manager_summary: str = Field(..., description="Tactical/operational focus with key metrics and departmental actions")
    level_3_executive_summary: str = Field(..., description="Full C-suite strategic narrative balancing performance and risk")
    level_4_board_summary: str = Field(..., description="Boardroom governance view highlighting strategic position and enterprise value")


class ExecutiveSummaryResult(BaseModel):
    """Standardized output schema for the Executive Summary Agent."""

    model_config = ConfigDict(from_attributes=True)

    executive_summary: str = Field(..., description="C-suite narrative synthesizing technical analysis into business decisions")
    key_findings: list[str] = Field(default_factory=list, description="Top high-signal findings and primary metric shifts")
    opportunities: list[str] = Field(default_factory=list, description="Identified growth, expansion, and optimization opportunities")
    risks: list[str] = Field(default_factory=list, description="Identified business, operational, and data risks")
    recommended_actions: list[str] = Field(default_factory=list, description="Prioritized recommendations across all horizons")
    business_health_score: int = Field(..., ge=0, le=100, description="Overall business health score (0-100)")
    priority_items: list[PriorityItem] = Field(default_factory=list, description="Priority-ranked items for rapid triage")

    # Enriched multi-level perspectives and categorized action horizons
    multi_level_summaries: MultiLevelSummaries | None = Field(
        default=None, description="Multi-tier summary representations (quick, manager, executive, board)"
    )
    immediate_actions: list[str] = Field(default_factory=list, description="Urgent actions required within 0-7 days")
    short_term_actions: list[str] = Field(default_factory=list, description="Tactical actions for the 30-90 day horizon")
    long_term_actions: list[str] = Field(default_factory=list, description="Strategic initiatives for 6-12 months")


class ExecutiveSummaryRequest(BaseModel):
    """Request payload for direct API summary generation."""

    results: dict[str, Any] = Field(default_factory=dict, description="Aggregated agent results (EDA, Stats, Validation, etc.)")
    query: str | None = Field(None, description="Original user query")
    dataset_id: str | None = Field(None, description="Dataset UUID")
    metadata: dict[str, Any] | None = Field(None, description="Dataset schema metadata")
    profile: dict[str, Any] | None = Field(None, description="Dataset statistical profile")
    quality: dict[str, Any] | None = Field(None, description="Dataset quality assessment")


class ExecutiveSummaryResponse(BaseModel):
    """API response envelope for executive summary."""

    model_config = ConfigDict(from_attributes=True)

    summary: ExecutiveSummaryResult = Field(..., description="Standardized executive summary output")
    dataset_id: str | None = Field(None, description="Target dataset ID")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO timestamp of summary generation",
    )
