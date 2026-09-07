"""Product Intelligence Dashboard (Phase 11.9).

Unified operational control center aggregating:
- Usage Metrics
- Quality Metrics
- Cost Metrics
- Forecast Metrics
- Recommendation Metrics
- System Health Status
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.operations.ab_testing import ab_testing_platform
from backend.operations.ai_quality_monitor import ai_quality_monitor
from backend.operations.continuous_learning import continuous_learning_pipeline
from backend.operations.cost_optimizer import cost_optimization_engine
from backend.operations.feedback_intelligence import feedback_intelligence
from backend.operations.model_evaluation import model_evaluation_framework
from backend.operations.product_analytics import product_analytics


class ProductIntelligenceDashboard:
    """Enterprise Operational Dashboard Synthesizer."""

    def __init__(
        self,
        analytics=product_analytics,
        quality=ai_quality_monitor,
        cost=cost_optimization_engine,
        feedback=feedback_intelligence,
        learning=continuous_learning_pipeline,
        eval_fw=model_evaluation_framework,
        ab_platform=ab_testing_platform,
    ) -> None:
        self.analytics = analytics
        self.quality = quality
        self.cost = cost
        self.feedback = feedback
        self.learning = learning
        self.eval_fw = eval_fw
        self.ab_platform = ab_platform

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Generate unified dashboard snapshot across all operational dimensions."""
        # 1. Usage Metrics
        usage = self.analytics.get_metrics()

        # 2. Quality Metrics
        quality_status = self.quality.get_status()

        # 3. Cost Metrics
        cost_analysis = self.cost.get_cost_analysis()

        # 4. Feedback & Recommendation Metrics
        feedback_analysis = self.feedback.generate_feedback_analytics()
        improvements = self.learning.get_improvements()

        # 5. Model Evaluations
        all_evals = self.eval_fw.get_all_reports()

        # 6. Overall System Health Determination
        quality_score = quality_status.get("quality_score", 100.0)
        has_alerts = quality_status.get("has_active_alerts", False)
        budget_pct = cost_analysis.get("budget_utilized_percent", 0.0)

        if quality_score < 75.0 or budget_pct > 100.0:
            health_status = "CRITICAL"
        elif quality_score < 90.0 or has_alerts or budget_pct > 80.0:
            health_status = "DEGRADED"
        else:
            health_status = "HEALTHY"

        dashboard_payload = {
            "dashboard": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "system_health": {
                    "status": health_status,
                    "overall_score": quality_score,
                    "active_quality_alerts": len(quality_status.get("alerts", [])),
                    "budget_utilized_percent": budget_pct,
                },
                "usage_metrics": {
                    "daily_active_users": usage["daily_active_users"],
                    "weekly_active_users": usage["weekly_active_users"],
                    "monthly_active_users": usage["monthly_active_users"],
                    "queries_executed": usage["queries_executed"],
                    "forecast_usage": usage["forecast_usage"],
                    "dataset_uploads": usage["dataset_uploads"],
                    "reports_generated": usage["reports_generated"],
                },
                "quality_metrics": {
                    "composite_quality_score": quality_score,
                    "active_alerts_count": len(quality_status.get("alerts", [])),
                    "total_defects_logged": quality_status.get("total_defects", 0),
                },
                "cost_metrics": {
                    "monthly_cost_usd": cost_analysis["monthly_cost"],
                    "monthly_budget_usd": cost_analysis["monthly_budget"],
                    "potential_savings_usd": cost_analysis["optimization_savings"],
                    "top_recommendation": cost_analysis["recommendations"][0]["title"] if cost_analysis["recommendations"] else "None",
                },
                "forecast_metrics": {
                    "total_runs": usage["forecast_usage"],
                    "latest_accuracy": all_evals.get("forecast_agent", [{}])[-1].get("accuracy", 1.0) if all_evals.get("forecast_agent") else 1.0,
                },
                "recommendation_metrics": {
                    "total_feedback_items": feedback_analysis["total_feedback"],
                    "pending_improvements": len(improvements["improvement_actions"]),
                },
            }
        }
        return dashboard_payload


product_dashboard = ProductIntelligenceDashboard()
