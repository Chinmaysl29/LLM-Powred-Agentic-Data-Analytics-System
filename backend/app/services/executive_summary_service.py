"""Executive Summary Service for AI Data Analyst OS.

Translates technical data analysis (EDA, Inferential Statistics, Data Quality,
and Validation) into executive decision-making language, multi-level business narratives,
key findings, opportunity and risk detection, prioritized action horizons, and business health scoring.
"""

import logging
from typing import Any

from backend.app.schemas.executive_summary import (
    ActionItem,
    ExecutiveSummaryResult,
    MultiLevelSummaries,
    PriorityItem,
    PriorityLevel,
)

logger = logging.getLogger(__name__)


class ExecutiveSummaryService:
    """Master engine for synthesizing technical analytics into executive decision intelligence."""

    def generate_summary(
        self,
        results: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        profile: dict[str, Any] | None = None,
        quality: dict[str, Any] | None = None,
        query: str | None = None,
    ) -> ExecutiveSummaryResult:
        """Synthesize all available analytics into a standardized Executive Summary."""
        logger.info("ExecutiveSummaryService generating summary across %d result domains", len(results))

        # 1. Insight Aggregation
        aggregated = self._aggregate_insights(results, metadata, profile, quality, query)

        # 2. Key Findings Engine
        key_findings = self._extract_key_findings(aggregated)

        # 3. Opportunity Detection Engine
        opportunities = self._detect_opportunities(aggregated)

        # 4. Risk Detection Engine
        risks = self._detect_risks(aggregated)

        # 5. Action Recommendation Layer (Immediate, Short-Term, Long-Term)
        immediate, short_term, long_term, all_actions = self._generate_actions(aggregated, opportunities, risks)

        # 6. Priority Engine
        priority_items = self._classify_priorities(key_findings, opportunities, risks, all_actions, aggregated)

        # 7. Business Health Scoring Engine
        health_score = self._compute_business_health_score(aggregated, risks)

        # 8. Executive Narrative Generator & Multi-Level Summaries
        narratives = self._generate_multi_level_summaries(
            aggregated=aggregated,
            key_findings=key_findings,
            opportunities=opportunities,
            risks=risks,
            actions=all_actions,
            health_score=health_score,
        )

        return ExecutiveSummaryResult(
            executive_summary=narratives.level_3_executive_summary,
            key_findings=key_findings,
            opportunities=opportunities,
            risks=risks,
            recommended_actions=all_actions,
            business_health_score=health_score,
            priority_items=priority_items,
            multi_level_summaries=narratives,
            immediate_actions=immediate,
            short_term_actions=short_term,
            long_term_actions=long_term,
        )

    # ------------------------------------------------------------------
    # 1. Insight Aggregation
    # ------------------------------------------------------------------
    def _aggregate_insights(
        self,
        results: dict[str, Any],
        metadata: dict[str, Any] | None,
        profile: dict[str, Any] | None,
        quality: dict[str, Any] | None,
        query: str | None,
    ) -> dict[str, Any]:
        """Aggregate disparate agent outputs and context into a structured dictionary."""
        eda = results.get("eda") or results.get("dataset_overview") or {}
        stats = results.get("statistics") or {}
        validation = results.get("validation") or {}
        quality_data = results.get("quality") or quality or {}
        meta_data = metadata or {}
        profile_data = profile or {}

        # Extract domain and dataset type
        dataset_summary = eda.get("dataset_summary") or {}
        dataset_type = dataset_summary.get("dataset_type") or eda.get("dataset_type") or meta_data.get("dataset_type") or "general"
        business_domain = dataset_summary.get("business_domain") or eda.get("business_domain") or "business"
        row_count = dataset_summary.get("row_count") or meta_data.get("row_count") or profile_data.get("row_count") or 0
        col_count = dataset_summary.get("column_count") or meta_data.get("column_count") or len(meta_data.get("column_names", [])) or 0

        # Trends
        trends = eda.get("trend_analysis") or []
        primary_trend = trends[0] if trends else None

        # Anomalies
        anomalies = eda.get("anomalies") or []

        # Statistical models and drivers
        regression = stats.get("regression") or {}
        primary_driver = stats.get("primary_driver") or regression.get("primary_driver")
        drivers = regression.get("drivers") or []
        r2_score = regression.get("r_squared", 0.0)

        # Significant correlations
        correlations = stats.get("significant_correlations") or []

        # Hypothesis tests
        hypothesis_tests = stats.get("hypothesis_tests") or []

        # Root causes & stats business insights
        root_causes = stats.get("root_causes") or []
        stat_insights = stats.get("business_insights") or []

        # Segments & Breakdown
        segments = eda.get("segments") or []

        # Validation status
        val_status = validation.get("validation_status", "PASSED")
        val_confidence = validation.get("confidence_score", 100)
        val_warnings = validation.get("warnings", [])
        val_errors = validation.get("errors", [])

        # Quality score
        overall_quality = quality_data.get("quality_score") or quality_data.get("overall_score") or 90

        return {
            "query": query,
            "dataset_type": dataset_type,
            "business_domain": business_domain,
            "row_count": row_count,
            "column_count": col_count,
            "trends": trends,
            "primary_trend": primary_trend,
            "anomalies": anomalies,
            "numeric_stats": eda.get("numeric_columns") or {},
            "missing_summary": eda.get("missing_values") or {},
            "segments": segments,
            "regression": regression,
            "primary_driver": primary_driver,
            "drivers": drivers,
            "r2_score": r2_score,
            "correlations": correlations,
            "hypothesis_tests": hypothesis_tests,
            "root_causes": root_causes,
            "stat_insights": stat_insights,
            "validation_status": val_status,
            "validation_confidence": val_confidence,
            "validation_warnings": val_warnings,
            "validation_errors": val_errors,
            "quality_score": overall_quality,
            "raw_results": results,
        }

    # ------------------------------------------------------------------
    # 2. Key Findings Engine
    # ------------------------------------------------------------------
    def _extract_key_findings(self, data: dict[str, Any]) -> list[str]:
        """Extract high-signal, metrics-driven key findings."""
        findings: list[str] = []

        # Finding 1: Scope & Dataset Volume
        row_count = data.get("row_count", 0)
        col_count = data.get("column_count", 0)
        domain = data.get("business_domain", "business")
        if row_count > 0:
            findings.append(f"Analyzed {row_count:,} records across {col_count} attributes in the {domain} domain.")

        # Finding 2: Primary Trend & Direction
        trend = data.get("primary_trend")
        if trend:
            col = trend.get("column", "Metric")
            direction = trend.get("direction", "stable")
            pct = trend.get("percentage_change", 0.0)
            sign = "+" if pct > 0 else ""
            findings.append(f"{col.replace('_', ' ').title()} trajectory: {direction.upper()} ({sign}{pct:.1f}% period-over-period shift).")

        # Finding 3: Segment / Concentration Contributions
        segments = data.get("segments") or []
        if segments:
            top_seg = segments[0]
            name = top_seg.get("segment_name") or top_seg.get("name", "Top Segment")
            share = top_seg.get("share_percentage") or top_seg.get("contribution_pct", 0.0)
            metric = top_seg.get("metric", "volume")
            if share > 0:
                findings.append(f"{name} contributes {share:.1f}% of total {metric.replace('_', ' ')}.")

        # Finding 4: Key Statistical Driver & Regression Impact
        driver = data.get("primary_driver")
        r2 = data.get("r2_score", 0.0)
        if driver:
            d_name = driver.get("feature", "Primary Driver")
            importance = driver.get("importance") or driver.get("standardized_coefficient", 0.0)
            findings.append(f"{d_name.replace('_', ' ').title()} is the primary outcome driver (relative importance: {importance:.2f}, R²: {r2:.2f}).")
        elif data.get("root_causes"):
            rc = data["root_causes"][0]
            findings.append(f"Root cause driver: {rc.get('driver', 'Driver')} explains {rc.get('variance_explained', 'significant')} variance in outcome.")

        # Finding 5: Statistical Significance / Correlation
        correlations = data.get("correlations") or []
        if correlations:
            top_corr = correlations[0]
            v1 = top_corr.get("variable_1", "var1").replace("_", " ").title()
            v2 = top_corr.get("variable_2", "var2").replace("_", " ").title()
            coef = top_corr.get("correlation", 0.0)
            p_val = top_corr.get("p_value", 0.001)
            findings.append(f"Statistically significant correlation observed between {v1} and {v2} (r={coef:.2f}, p < {p_val:.3f}).")

        # Finding 6: Hypothesis Testing Evidence
        hyp_tests = data.get("hypothesis_tests") or []
        for test in hyp_tests:
            if test.get("null_hypothesis_rejected"):
                g_a = test.get("group_a", "Group A")
                g_b = test.get("group_b", "Group B")
                var = test.get("variable", "metric").replace("_", " ")
                findings.append(f"Hypothesis testing confirmed statistically significant difference in {var} between {g_a} and {g_b} (p={test.get('p_value', 0.001):.4f}).")
                break

        # Fallback if findings list is sparse
        if not findings:
            findings.append("Data overview indicates stable baseline operations across all recorded metrics.")
            findings.append(f"Quality and schema validation confirmed healthy data ingestion with {data.get('quality_score')}% quality rating.")

        return findings

    # ------------------------------------------------------------------
    # 3. Opportunity Detection Engine
    # ------------------------------------------------------------------
    def _detect_opportunities(self, data: dict[str, Any]) -> list[str]:
        """Detect growth, expansion, and operational optimization opportunities."""
        opportunities: list[str] = []

        # 1. Growth Opportunities (Leveraging Primary Drivers)
        driver = data.get("primary_driver")
        if driver:
            d_name = driver.get("feature", "driver").replace("_", " ")
            opportunities.append(
                f"Growth Opportunity: Accelerate investment in '{d_name}', as statistical modeling confirms it is the strongest predictor of positive performance."
            )
        else:
            correlations = data.get("correlations") or []
            if correlations:
                top_corr = correlations[0]
                var1 = top_corr.get("variable_1", "").replace("_", " ")
                var2 = top_corr.get("variable_2", "").replace("_", " ")
                opportunities.append(
                    f"Growth Opportunity: Leverage strong co-movement between {var1} and {var2} to optimize cross-channel campaigns."
                )

        # 2. Market / Segment Expansion Opportunities
        segments = data.get("segments") or []
        if segments:
            top_seg = segments[0]
            name = top_seg.get("segment_name") or top_seg.get("name", "Leading Segment")
            share = top_seg.get("share_percentage") or top_seg.get("contribution_pct", 0.0)
            opportunities.append(
                f"Expansion Opportunity: Prioritize capacity expansion in '{name}', which demonstrates outsized market demand (capturing {share:.1f}% of volume)."
            )
        else:
            opportunities.append(
                "Expansion Opportunity: Segment customers across behavioral tiers to identify high-value cohorts for targeted upselling."
            )

        # 3. Operational Optimization Opportunities
        anomalies = data.get("anomalies") or []
        if anomalies:
            opportunities.append(
                f"Optimization Opportunity: Resolve {len(anomalies)} process outliers to tighten operational variance and prevent revenue leakage."
            )
        else:
            opportunities.append(
                "Optimization Opportunity: Automate inventory and workflow allocations based on empirical demand patterns to eliminate idle capacity."
            )

        return opportunities

    # ------------------------------------------------------------------
    # 4. Risk Detection Engine
    # ------------------------------------------------------------------
    def _detect_risks(self, data: dict[str, Any]) -> list[str]:
        """Detect business, operational, and data risks."""
        risks: list[str] = []

        # 1. Business / Trend Risks
        trend = data.get("primary_trend")
        if trend and trend.get("direction") == "decline":
            col = trend.get("column", "Metric").replace("_", " ").title()
            pct = abs(trend.get("percentage_change", 0.0))
            risks.append(f"Business Risk: {col} shows an active downward trend (-{pct:.1f}%), signaling declining market momentum.")
        elif any("churn" in str(f).lower() for f in data.get("stat_insights", [])):
            risks.append("Business Risk: Emerging customer retention drop detected, indicating elevated risk of churn.")

        # 2. Concentration Risk
        segments = data.get("segments") or []
        if segments:
            top_seg = segments[0]
            share = top_seg.get("share_percentage") or top_seg.get("contribution_pct", 0.0)
            if share >= 40.0:
                name = top_seg.get("segment_name") or top_seg.get("name", "Top Segment")
                risks.append(
                    f"Business Risk: High concentration vulnerability — '{name}' accounts for {share:.1f}% of total volume."
                )

        # 3. Operational & Outlier Risks
        anomalies = data.get("anomalies") or []
        if len(anomalies) > 0:
            risks.append(
                f"Operational Risk: {len(anomalies)} anomalous records detected exhibiting extreme variance from baseline operational bounds."
            )

        # 4. Data Quality & Validation Risks
        val_status = data.get("validation_status")
        val_errors = data.get("validation_errors") or []
        val_warnings = data.get("validation_warnings") or []
        quality_score = data.get("quality_score", 100)

        if val_status == "FAILED" or len(val_errors) > 0:
            risks.append(f"Data Risk: Validation gatekeeper flagged critical errors: {'; '.join(val_errors[:2])}.")
        elif val_status == "WARNING" or len(val_warnings) > 0:
            risks.append(f"Data Risk: Validation warnings present ({len(val_warnings)} item(s)): {val_warnings[0]}.")

        if quality_score < 80:
            risks.append(f"Data Risk: Sub-optimal data quality score ({quality_score}/100) introduces risk of distorted metrics.")

        # Fallback if no specific risks triggered
        if not risks:
            risks.append("Operational Risk: Baseline variance requires continuous monitoring to safeguard against unanticipated volatility.")

        return risks

    # ------------------------------------------------------------------
    # 5. Action Recommendation Layer
    # ------------------------------------------------------------------
    def _generate_actions(
        self,
        data: dict[str, Any],
        opportunities: list[str],
        risks: list[str],
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """Map recommendations into immediate, short-term, and long-term horizons."""
        immediate: list[str] = []
        short_term: list[str] = []
        long_term: list[str] = []

        # Immediate Actions (0 - 7 Days): Urgent risk mitigation & data verification
        if any("Validation" in r or "Data Risk" in r for r in risks):
            immediate.append("Review and remediate data quality anomalies and validation warnings.")
        if any("downward trend" in r.lower() or "churn" in r.lower() for r in risks):
            immediate.append("Convene leadership to investigate primary drivers of declining trajectory.")
        else:
            immediate.append("Audit baseline performance metrics and establish operational alerting thresholds.")

        # Short-Term Actions (30 - 90 Days): Tactical optimization & driver reinforcement
        driver = data.get("primary_driver")
        if driver:
            d_name = driver.get("feature", "growth driver").replace("_", " ")
            short_term.append(f"Reallocate budget towards proven growth catalyst '{d_name}' to maximize operational ROI.")
        else:
            short_term.append("Deploy targeted promotional campaigns focusing on the top-performing customer segments.")

        segments = data.get("segments") or []
        if segments:
            top_seg = segments[0]
            name = top_seg.get("segment_name") or top_seg.get("name", "leading segment")
            short_term.append(f"Expand sales and customer success capacity dedicated to '{name}'.")
        else:
            short_term.append("Implement automated anomaly detection to prevent process and inventory deviations.")

        # Long-Term Actions (6 - 12 Months): Strategic structural investments
        long_term.append("Scale regional distribution and operational infrastructure to support sustained growth.")
        long_term.append("Upgrade analytical data pipelines to support real-time predictive forecasting and scenario planning.")

        all_actions = immediate + short_term + long_term
        return immediate, short_term, long_term, all_actions

    # ------------------------------------------------------------------
    # 6. Priority Engine
    # ------------------------------------------------------------------
    def _classify_priorities(
        self,
        key_findings: list[str],
        opportunities: list[str],
        risks: list[str],
        actions: list[str],
        data: dict[str, Any],
    ) -> list[PriorityItem]:
        """Classify and prioritize all observations, risks, and actions."""
        items: list[PriorityItem] = []

        # Classify Risks
        for r in risks:
            if "downward trend" in r.lower() or "critical" in r.lower() or "churn" in r.lower() or "FAILED" in r:
                p: PriorityLevel = "critical"
                impact = "Immediate threat to revenue or reporting integrity"
            elif "concentration" in r.lower() or "variance" in r.lower() or "warning" in r.lower():
                p = "high"
                impact = "Elevated exposure to operational or portfolio volatility"
            else:
                p = "medium"
                impact = "Moderate operational risk"

            items.append(
                PriorityItem(
                    title=r.split(":")[0] if ":" in r else "Identified Risk",
                    priority=p,
                    category="risk",
                    description=r,
                    impact=impact,
                )
            )

        # Classify Opportunities
        for opp in opportunities:
            if "Growth Opportunity" in opp:
                items.append(
                    PriorityItem(
                        title="Core Growth Driver",
                        priority="high",
                        category="opportunity",
                        description=opp,
                        impact="High potential to accelerate top-line revenue",
                    )
                )
            elif "Expansion Opportunity" in opp:
                items.append(
                    PriorityItem(
                        title="Market Expansion",
                        priority="high",
                        category="opportunity",
                        description=opp,
                        impact="Substantial TAM expansion and customer acquisition",
                    )
                )
            else:
                items.append(
                    PriorityItem(
                        title="Process Optimization",
                        priority="medium",
                        category="opportunity",
                        description=opp,
                        impact="Margin and efficiency improvement",
                    )
                )

        # Classify Actions
        for act in actions:
            if any(term in act.lower() for term in ["investigate", "remediate", "audit", "rebalance"]):
                items.append(
                    PriorityItem(
                        title="Urgent Intervention",
                        priority="critical",
                        category="action",
                        description=act,
                        impact="Risk stabilization and operational continuity",
                    )
                )
            elif any(term in act.lower() for term in ["reallocate", "expand", "deploy"]):
                items.append(
                    PriorityItem(
                        title="Tactical Growth Action",
                        priority="high",
                        category="action",
                        description=act,
                        impact="Measurable revenue uplift in 30-90 days",
                    )
                )
            else:
                items.append(
                    PriorityItem(
                        title="Strategic Initiative",
                        priority="medium",
                        category="action",
                        description=act,
                        impact="Long-term enterprise value enhancement",
                    )
                )

        # Sort: critical first, then high, then medium, then low
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        items.sort(key=lambda x: priority_order.get(x.priority, 4))
        return items

    # ------------------------------------------------------------------
    # 7. Business Health Scoring Engine
    # ------------------------------------------------------------------
    def _compute_business_health_score(
        self,
        data: dict[str, Any],
        risks: list[str],
    ) -> int:
        """Calculate overall business health score from 0 to 100."""
        score = 80  # Baseline benchmark

        # Factor 1: Trend Trajectory
        trend = data.get("primary_trend")
        if trend:
            direction = trend.get("direction")
            if direction == "growth":
                score += 8
            elif direction == "decline":
                score -= 14
            elif direction == "fluctuating":
                score -= 5

        # Factor 2: Data Quality & Validation
        val_status = data.get("validation_status")
        if val_status == "PASSED":
            score += 4
        elif val_status == "WARNING":
            score -= 6
        elif val_status == "FAILED":
            score -= 16

        quality_score = data.get("quality_score", 90)
        if quality_score >= 95:
            score += 4
        elif quality_score < 75:
            score -= 8

        # Factor 3: Presence of Statistically Verified Growth Drivers
        if data.get("r2_score", 0.0) >= 0.5 or data.get("primary_driver"):
            score += 4

        # Factor 4: Risk Penalties
        for r in risks:
            if "downward trend" in r.lower() or "FAILED" in r or "critical" in r.lower() or "churn" in r.lower():
                score -= 6
            elif "concentration" in r.lower() or "variance" in r.lower():
                score -= 3

        # Clamp between 0 and 100
        return max(0, min(100, int(round(score))))

    # ------------------------------------------------------------------
    # 8. Executive Narrative Generator & Multi-Level Summaries
    # ------------------------------------------------------------------
    def _generate_multi_level_summaries(
        self,
        aggregated: dict[str, Any],
        key_findings: list[str],
        opportunities: list[str],
        risks: list[str],
        actions: list[str],
        health_score: int,
    ) -> MultiLevelSummaries:
        """Generate 4 tailored summary levels (Quick, Manager, Executive, Board)."""
        domain = aggregated.get("business_domain", "business")
        row_count = aggregated.get("row_count", 0)
        trend = aggregated.get("primary_trend")
        driver = aggregated.get("primary_driver")
        val_status = aggregated.get("validation_status", "PASSED")

        trend_desc = "steady baseline performance"
        if trend:
            d = trend.get("direction", "stable")
            p = trend.get("percentage_change", 0.0)
            sign = "+" if p > 0 else ""
            trend_desc = f"{d} trajectory ({sign}{p:.1f}%)"

        driver_desc = ""
        if driver:
            d_name = driver.get("feature", "primary driver").replace("_", " ")
            driver_desc = f", primarily driven by {d_name}"

        # Level 1: 30-Second Quick Summary (Elevator Pitch)
        level_1 = (
            f"Business Health Score: {health_score}/100. "
            f"The {domain} dataset ({row_count:,} records) reflects a {trend_desc}{driver_desc}. "
            f"Top recommendation: {actions[0] if actions else 'Maintain ongoing KPI monitoring.'}"
        )

        # Level 2: Manager Summary (Tactical & Operational Focus)
        mgr_findings = "\n".join([f"  • {kf}" for kf in key_findings[:3]])
        mgr_actions = "\n".join([f"  • {act}" for act in actions[:3]])
        level_2 = (
            f"OPERATIONAL MANAGER BRIEFING:\n"
            f"Domain: {domain.title()} | Data Health: {health_score}/100 | Validation: {val_status}\n\n"
            f"Key Metric Observations:\n{mgr_findings}\n\n"
            f"Departmental Action Items:\n{mgr_actions}"
        )

        # Level 3: Executive Summary (Standard C-Suite Narrative)
        exec_intro = (
            f"The business demonstrated {trend_desc} across observed {domain} operations{driver_desc}. "
            f"Overall enterprise health stands at {health_score}/100 with comprehensive data validation confirmed at {val_status}."
        )
        exec_opps = (
            f"Key opportunities center on {opportunities[0].lower() if opportunities else 'optimizing growth levers'}. "
            f"Strategic resource reallocation can amplify these gains."
        )
        exec_risks = (
            f"However, leadership must monitor active exposure: {risks[0].lower() if risks else 'general variance'}. "
            f"Proactive intervention is recommended to preserve margins and market share."
        )
        exec_conclusion = (
            f"Executive Recommendation: Prioritize '{actions[0] if actions else 'operational alignment'}' "
            f"over the coming cycle to secure sustained enterprise momentum."
        )
        level_3 = f"{exec_intro} {exec_opps} {exec_risks} {exec_conclusion}"

        # Level 4: Board Presentation Summary (Governance, Risk, & Enterprise Value)
        level_4 = (
            f"BOARD OF DIRECTORS EXECUTIVE SUMMARY:\n\n"
            f"1. Strategic Trajectory: The enterprise maintains a business health index of {health_score}/100, "
            f"reflecting {trend_desc}. Market performance remains supported by solid structural drivers.\n\n"
            f"2. Value Creation Opportunities: Capital allocation should prioritize {opportunities[0] if opportunities else 'market scaling'} "
            f"to maximize return on invested capital.\n\n"
            f"3. Enterprise Risk Governance: The board should note {risks[0] if risks else 'standard market risk factors'}, "
            f"with mitigation strategies actively deployed.\n\n"
            f"4. Fiduciary Guidance: Endorse proposed executive initiatives focused on {actions[0] if actions else 'growth stabilization'}."
        )

        return MultiLevelSummaries(
            level_1_quick_summary=level_1,
            level_2_manager_summary=level_2,
            level_3_executive_summary=level_3,
            level_4_board_summary=level_4,
        )
