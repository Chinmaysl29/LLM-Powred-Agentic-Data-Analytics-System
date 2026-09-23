"""Unit and Integration Tests for Phase 11.10: Continuous Improvement Orchestrator.

Validates the 4 Final Enterprise Test Cases:
- Test Case 1: User Feedback Submitted -> Expected: Stored + Categorized
- Test Case 2: Model Accuracy Drops -> Expected: Alert Generated
- Test Case 3: Cloud Cost Increases -> Expected: Optimization Recommendation
- Test Case 4: New Model Outperforms Current Model -> Expected: A/B Test Winner Selected

Also validates composite platform health scoring (0-100) and roadmap synthesis.
"""

import pytest
from backend.operations.ab_testing import ABTestingPlatform, MetricDirection
from backend.operations.ai_quality_monitor import AIQualityMonitor, QualityDefectType
from backend.operations.continuous_improvement_orchestrator import (
    ContinuousImprovementOrchestrator,
)
from backend.operations.continuous_learning import ContinuousLearningPipeline, LearningSource
from backend.operations.cost_optimizer import CostCategory, CostOptimizationEngine
from backend.operations.feedback_intelligence import FeedbackChannel, UserFeedbackIntelligence
from backend.operations.feature_flags import FeatureFlagSystem
from backend.operations.model_evaluation import EvaluatedAgent, ModelEvaluationFramework
from backend.operations.product_analytics import ProductAnalyticsEngine, UsageEventType


@pytest.fixture
def clean_orchestrator():
    feedback = UserFeedbackIntelligence()
    analytics = ProductAnalyticsEngine()
    model_eval = ModelEvaluationFramework()
    quality = AIQualityMonitor(alert_threshold=90.0)
    ab_testing = ABTestingPlatform()
    feature_flags = FeatureFlagSystem()
    cost_optimizer = CostOptimizationEngine(monthly_budget_usd=1000.0)
    learning = ContinuousLearningPipeline()

    return ContinuousImprovementOrchestrator(
        feedback=feedback,
        analytics=analytics,
        model_eval=model_eval,
        quality=quality,
        ab_testing=ab_testing,
        feature_flags=feature_flags,
        cost_optimizer=cost_optimizer,
        learning=learning,
    )


def test_enterprise_test_case_1_feedback_stored_and_categorized(clean_orchestrator):
    """Test Case 1: User Feedback Submitted -> Expected: Stored + Categorized."""
    res = clean_orchestrator.feedback.capture_feedback(
        description="Query latency is too slow for big tables",
        channel=FeedbackChannel.CHAT,
        user_id="user_corp_1",
    )
    assert res["feedback_id"].startswith("fb_")
    assert res["feedback_type"] == "PERFORMANCE"
    assert res["priority"] in ["HIGH", "CRITICAL"]

    # Verify retrieval from repository
    stored = clean_orchestrator.feedback.get_feedback(res["feedback_id"])
    assert stored is not None
    assert stored["description"] == "Query latency is too slow for big tables"


def test_enterprise_test_case_2_model_accuracy_drops_generates_alert(clean_orchestrator):
    """Test Case 2: Model Accuracy Drops -> Expected: Alert Generated."""
    # Report defects causing score to drop below 90.0
    clean_orchestrator.quality.report_defect(
        defect_type=QualityDefectType.INCORRECT_SQL,
        component="sql_agent",
        details="Subquery syntax failure on PostgreSQL 16",
    )
    clean_orchestrator.quality.report_defect(
        defect_type=QualityDefectType.INCORRECT_SQL,
        component="sql_agent",
        details="Table alias collision in join predicate",
    )

    status = clean_orchestrator.quality.get_status()
    assert status["quality_score"] < 90.0
    assert status["has_active_alerts"] is True
    assert len(status["alerts"]) >= 1
    assert "sql_agent" in status["alerts"][0]["component"]


def test_enterprise_test_case_3_cloud_cost_increases_gives_recommendation(clean_orchestrator):
    """Test Case 3: Cloud Cost Increases -> Expected: Optimization Recommendation."""
    # Record heavy OpenAI spend ($500)
    clean_orchestrator.cost_optimizer.record_usage(
        category=CostCategory.OPENAI,
        units=100_000_000,
        metadata={"job": "batch_forecasting_classification"},
    )

    cost_analysis = clean_orchestrator.cost_optimizer.get_cost_analysis()
    assert cost_analysis["monthly_cost"] == 500.0
    assert cost_analysis["optimization_savings"] > 100.0
    recs = cost_analysis["recommendations"]
    assert len(recs) >= 1
    assert any("Groq" in r["description"] or "Routing" in r["title"] for r in recs)


def test_enterprise_test_case_4_new_model_outperforms_winner_selected(clean_orchestrator):
    """Test Case 4: New Model Outperforms Current Model -> Expected: A/B Test Winner Selected."""
    exp = clean_orchestrator.ab_testing.create_experiment(
        name="LLaMA-3.3 70B vs GPT-4o",
        variant_a="gpt-4o",
        variant_b="llama-3.3-70b",
        primary_metric="accuracy",
        direction=MetricDirection.HIGHER_IS_BETTER,
        min_samples=20,
    )
    exp_id = exp["experiment_id"]

    for _ in range(25):
        clean_orchestrator.ab_testing.record_result(exp_id, variant="gpt-4o", metric_value=0.88)
        clean_orchestrator.ab_testing.record_result(exp_id, variant="llama-3.3-70b", metric_value=0.96)

    winner_report = clean_orchestrator.ab_testing.evaluate_winner(exp_id)
    assert winner_report["winner"] == "llama-3.3-70b"
    assert winner_report["statistically_significant"] is True
    assert winner_report["delta"] == 0.08


def test_orchestrator_platform_health_and_roadmap(clean_orchestrator):
    """Verify composite platform health calculation and roadmap task synthesis."""
    # Baseline clean state
    clean_cycle = clean_orchestrator.generate_orchestration_cycle()
    assert clean_cycle["platform_health"] == 100.0
    assert clean_cycle["status"] == "EXCELLENT"
    assert len(clean_cycle["improvement_plan"]) >= 1

    # Inject learning corrections and high costs
    clean_orchestrator.learning.record_learning_event(
        source=LearningSource.QUERY_HISTORY,
        target_component="sql_agent",
        original_input="Query 1",
        user_correction="Correction 1",
    )
    clean_orchestrator.learning.record_learning_event(
        source=LearningSource.QUERY_HISTORY,
        target_component="sql_agent",
        original_input="Query 2",
        user_correction="Correction 2",
    )
    clean_orchestrator.cost_optimizer.record_usage(
        category=CostCategory.OPENAI,
        units=100_000_000,
    )

    # Re-run cycle
    cycle = clean_orchestrator.generate_orchestration_cycle()
    assert len(cycle["improvement_plan"]) >= 2
    task_areas = [t["area"] for t in cycle["improvement_plan"]]
    assert "Autonomous Agent Quality" in task_areas or "Cloud & AI Unit Economics" in task_areas
