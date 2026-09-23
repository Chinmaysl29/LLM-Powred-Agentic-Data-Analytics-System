"""
Phase 13 — Production Operations & Business Readiness Tests
Validates:
1. 13.1 CI/CD Platform (Build, Canary Deploy, Automated Rollback)
2. 13.2 Infrastructure as Code (Dev, Staging, Production & Terraform Validation)
3. 13.3 Security Operations (Vulnerability Scan, Secret Rotation, Tamper-Evident Audit, Pen Test)
4. 13.4 Performance Engineering (Load Test, Stress Limits, Query Optimization, Cache Hit Ratio)
5. 13.5 Reliability Engineering (99.99% SLA, Error Budget Burn, Incident Response)
6. 13.6 Product Analytics (DAU/MAU Stickiness, Feature Usage, Forecast MAPE/RMSE, Business KPIs)
7. 13.7 Billing Platform (Subscriptions, Usage Credits Metering, Invoicing, Enterprise Contracts)
8. 13.8 Customer Success Platform (Onboarding Flows, Knowledge Base Search, Support Desk, NPS)
9. 13.9 AI Governance (Prompt Versioning, Token Cost Tracking, AI Audit Trail, Explainability)
10. 13.10 Enterprise Certification & Readiness Report (SOC2, ISO 27001, GDPR, HIPAA, Data Retention)
"""

import json
import pytest
from backend.operations.cicd_platform import CICDPlatformEngine, PipelineStatus, DeploymentStrategy
from backend.operations.iac_manager import IaCManager, TargetEnvironment
from backend.operations.secops import SecOpsPlatform
from backend.operations.performance_engineering import PerformanceEngineeringPlatform
from backend.operations.reliability_engineering import ReliabilityPlatform, IncidentSeverity
from backend.operations.product_analytics import ProductAnalyticsEngine
from backend.operations.billing_platform import BillingPlatformEngine, SubscriptionTier
from backend.operations.customer_success import CustomerSuccessPlatform
from backend.operations.ai_governance import AIGovernancePlatform
from backend.operations.compliance_certification import ComplianceCertificationPlatform


def test_13_1_cicd_platform():
    """Test automated pipeline execution, canary deployment, and health failure rollback."""
    cicd = CICDPlatformEngine()

    # 1. Successful Canary Deployment
    res = cicd.run_pipeline(
        commit_sha="a1b2c3d4e5f67890",
        branch="main",
        target_env="production",
        strategy=DeploymentStrategy.CANARY,
        simulate_health_failure=False
    )
    assert res.status == PipelineStatus.SUCCESS
    assert res.rollback_performed is False
    assert "docker_build_and_publish" in res.stages_executed
    assert cicd.get_deployed_image("production").startswith("analystos/backend:")

    # 2. Deployment Failure & Automated Rollback
    bad_res = cicd.run_pipeline(
        commit_sha="deadbeef99999999",
        branch="main",
        target_env="production",
        strategy=DeploymentStrategy.CANARY,
        simulate_health_failure=True
    )
    assert bad_res.status == PipelineStatus.ROLLED_BACK
    assert bad_res.rollback_performed is True
    assert "automated_rollback_triggered" in bad_res.stages_executed


def test_13_2_infrastructure_as_code():
    """Test Dev, Staging, and Production environment governance and Terraform plan validation."""
    iac = IaCManager()

    # 1. Dev Environment Quotas
    dev_cfg = iac.get_environment_config(TargetEnvironment.DEV)
    assert dev_cfg.cluster_nodes == 2
    assert dev_cfg.monthly_budget_usd == 300.0

    # 2. Production Multi-Region Enforcement
    prod_cfg = iac.get_environment_config(TargetEnvironment.PRODUCTION)
    assert prod_cfg.multi_region is True
    assert prod_cfg.enforce_strict_tls is True

    # 3. Terraform Plan Validation
    valid_plan = [
        "module.vpc.aws_vpc.main",
        "module.k8s_cluster.aws_eks_cluster.core",
        "module.rds_postgres.aws_rds_cluster.primary",
        "module.rds_postgres.aws_rds_cluster_instance.replica_region_eu",
        "module.elasticache_redis.aws_elasticache_replication_group.cache"
    ]
    val_res = iac.validate_terraform_plan(TargetEnvironment.PRODUCTION, valid_plan)
    assert val_res["valid"] is True
    assert val_res["resource_count"] == 5

    # Missing multi-region in prod should fail
    bad_plan = [
        "module.vpc.aws_vpc.main",
        "module.k8s_cluster.aws_eks_cluster.core",
        "module.rds_postgres.aws_rds_cluster.primary",
        "module.elasticache_redis.aws_elasticache_replication_group.cache"
    ]
    bad_val = iac.validate_terraform_plan(TargetEnvironment.PRODUCTION, bad_plan)
    assert bad_val["valid"] is False

    # 4. K8s Manifest Generation
    manifest = iac.render_environment_manifest(TargetEnvironment.STAGING)
    assert manifest["kind"] == "ResourceQuota"
    assert manifest["spec"]["hard"]["pods"] == "15"


def test_13_3_security_operations():
    """Test vulnerability scanning, secret rotation, tamper-evident audit trails, and pen test suite."""
    sec = SecOpsPlatform()

    # 1. Vulnerability Scanning
    clean_scan = sec.run_vulnerability_scan("analystos/backend", simulate_flaws=False)
    assert clean_scan.passed is True
    assert clean_scan.critical_count == 0

    vuln_scan = sec.run_vulnerability_scan("legacy-third-party-dep", simulate_flaws=True)
    assert vuln_scan.passed is False
    assert vuln_scan.critical_count == 2

    # 2. Secret Rotation
    rot = sec.rotate_secret("RDS_PASSWORD", "NewStrongSecret99!")
    assert rot["version"] == 1
    assert "hash" in rot

    # 3. Tamper-Evident Audit Trail
    sec.record_audit_log("admin_alice", "UPDATE_RBAC_POLICY", {"role": "financial_auditor"})
    sec.record_audit_log("admin_bob", "REVOKE_API_KEY", {"key_id": "key-109"})
    trail = sec.get_audit_trail()
    assert len(trail) >= 3
    # Check cryptographic chain link
    assert trail[-1]["prev_hash"] == trail[-2]["log_hash"]

    # 4. Penetration Testing
    pentest = sec.run_penetration_test_suite()
    assert pentest["status"] == "PASSED_SECURE"
    assert pentest["vulnerabilities_exploited"] == 0


def test_13_4_performance_engineering():
    """Test synthetic load testing, stress saturation, query plan optimization, and caching SLA."""
    perf = PerformanceEngineeringPlatform()

    # 1. Load Test (1000 Virtual Users)
    bench = perf.run_load_test(virtual_users=1000, duration_seconds=10)
    assert bench.passed is True
    assert bench.p95_latency_ms < 100.0
    assert bench.successful_requests == 50000

    # 2. Stress Test (Breaking Point)
    stress = perf.run_stress_test(max_virtual_users=50000)
    assert stress["breaking_point_vus"] == 45000
    assert stress["safe_operating_capacity_vus"] > 30000

    # 3. Database Optimization
    opt = perf.optimize_database_query("reports", "SELECT * FROM reports WHERE tenant_id = 't1' ORDER BY created_at")
    assert "speedup_factor" in opt
    assert opt["optimized_cost"] < opt["original_cost"]

    # 4. Caching Evaluation
    cache_eval = perf.evaluate_caching_performance(hits=9400, misses=600)
    assert cache_eval["hit_ratio"] == 0.94
    assert cache_eval["target_met"] is True


def test_13_5_reliability_engineering():
    """Test 99.99% availability calculation, error budget consumption, and incident triage."""
    sre = ReliabilityPlatform(target_availability=0.9999)

    # 1. SLO / SLA & Error Budget
    slo = sre.calculate_slo_metrics()
    assert slo["target_sla"] == 0.9999
    assert slo["actual_availability"] > 0.9999
    assert slo["remaining_failure_budget"] > 0
    assert slo["sla_breached"] is False

    # 2. Incident Management
    inc = sre.trigger_incident(
        title="Cache Connection Timeout in EU Region",
        severity=IncidentSeverity.P2_MAJOR,
        impacted_services=["redis-cluster-eu", "forecast-agent"]
    )
    assert inc.status == "OPEN"

    resolved = sre.resolve_incident(inc.incident_id, "Redis replica promoted after network partition healed.")
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_at is not None

    # 3. Disaster Recovery Drill
    drill = sre.run_dr_failover_drill()
    assert drill["result"] == "PASSED"
    assert drill["failover_duration_sec"] < 10.0


def test_13_6_product_analytics():
    """Test user engagement cohorts, feature adoption distributions, forecast MAPE/RMSE, and business KPIs."""
    analytics = ProductAnalyticsEngine()

    # 1. User Engagement & Retention
    eng = analytics.get_user_engagement_metrics()
    assert eng["dau"] == 42500
    assert eng["mau"] == 125000
    assert eng["dau_mau_ratio"] > 0.30

    # 2. Feature Adoption
    adopt = analytics.get_feature_adoption()
    assert adopt["total_feature_invocations"] > 70000
    assert adopt["most_active_feature"] == "sql_agent"

    # 3. Forecast Accuracy (MAPE & RMSE)
    actuals = [100.0, 110.0, 125.0, 140.0, 160.0]
    predictions = [102.0, 108.0, 122.0, 144.0, 158.0]
    acc = analytics.evaluate_forecast_accuracy(actuals, predictions)
    assert acc["mape_percentage"] < 5.0 # Less than 5% error
    assert acc["accuracy_grade"] == "EXCELLENT"

    # 4. Recommendation Click-Through
    rec_metrics = analytics.get_recommendation_acceptance_metrics()
    assert rec_metrics["acceptance_rate"] == 0.82

    # 5. SaaS Financial KPIs
    kpis = analytics.get_business_kpis()
    assert kpis["annual_recurring_revenue_usd"] == 14500000.0
    assert kpis["net_revenue_retention"] == 1.28


def test_13_7_billing_platform():
    """Test tiered subscriptions, usage credit meters, automated invoicing, and enterprise contracts."""
    billing = BillingPlatformEngine()

    # 1. Subscription & Initial Credits
    sub = billing.create_subscription("tenant-acme", SubscriptionTier.PRO)
    assert sub["tier"] == "PRO"
    assert sub["initial_credits"] == 50000

    # 2. Usage Tracking & Credit Deduction
    use1 = billing.track_usage("tenant-acme", compute_units=250.0, service_name="sql_analytics")
    assert use1["success"] is True
    assert use1["remaining_credits"] == 49750.0

    # Insufficient credits check
    billing._credit_balances["tenant-broke"] = 10.0
    use2 = billing.track_usage("tenant-broke", compute_units=500.0, service_name="deep_forecasting")
    assert use2["success"] is False

    # 3. Add Credits
    new_bal = billing.add_credits("tenant-acme", 10000.0)
    assert new_bal == 59750.0

    # 4. Invoice Generation
    inv = billing.generate_invoice("tenant-acme", additional_charges=50.0)
    assert inv.amount_usd == 549.0 # $499 base + $50 overages
    assert inv.status == "PAID"

    # 5. Enterprise Contract Registration
    contract = billing.register_enterprise_contract(
        tenant_id="tenant-megacorp",
        annual_contract_value=120000.0,
        term_years=3,
        discount_percentage=25.0
    )
    assert contract["status"] == "EXECUTED"
    assert contract["acv"] == 120000.0


def test_13_8_customer_success():
    """Test onboarding checklists, Knowledge Base indexing, support ticketing, and NPS capture."""
    cs = CustomerSuccessPlatform()

    # 1. Onboarding Progress
    cs.init_onboarding("tenant-newco")
    step1 = cs.complete_onboarding_step("tenant-newco", "connect_first_dataset")
    assert step1["progress_percentage"] == 25.0
    assert step1["all_complete"] is False

    cs.complete_onboarding_step("tenant-newco", "run_first_eda")
    cs.complete_onboarding_step("tenant-newco", "invite_team_members")
    final_step = cs.complete_onboarding_step("tenant-newco", "setup_notifications")
    assert final_step["progress_percentage"] == 100.0
    assert final_step["all_complete"] is True

    # 2. Knowledge Base Search
    articles = cs.search_kb("Snowflake")
    assert len(articles) >= 1
    assert "Snowflake" in articles[0]["title"]

    # 3. Support Ticket Lifecycle
    ticket = cs.create_support_ticket(
        tenant_id="tenant-newco",
        user_email="admin@newco.com",
        subject="Request for custom connector review",
        description="Need review for internal CRM connector.",
        priority="HIGH"
    )
    assert ticket.status == "OPEN"

    cs.reply_ticket(ticket.ticket_id, author="Support Engineer", text="Review initiated.")
    assert ticket.status == "IN_PROGRESS"
    assert len(ticket.responses) == 1

    cs.resolve_ticket(ticket.ticket_id)
    assert ticket.status == "RESOLVED"

    # 4. Customer Feedback (NPS)
    nps = cs.submit_nps_survey("tenant-newco", score=10, comment="Platform is exceptionally fast.")
    assert nps["category"] == "PROMOTER"


def test_13_9_ai_governance():
    """Test prompt versioning, inference token cost tracking, immutable audit trail, and explainability."""
    gov = AIGovernancePlatform()

    # 1. Prompt Management
    p1 = gov.register_prompt("eda_summary_prompt", "Summarize dataframe statistics for {dataset_name}", ["dataset_name"])
    assert p1.version == 1

    p2 = gov.register_prompt("eda_summary_prompt", "Summarize dataframe and identify outliers for {dataset_name}", ["dataset_name"])
    assert p2.version == 2

    latest = gov.get_latest_prompt("eda_summary_prompt")
    assert latest.version == 2

    # 2. AI Inference Cost Tracking & Cryptographic Audit Entry
    audit_entry = gov.log_ai_inference(
        tenant_id="tenant-acme",
        user_id="analyst-1",
        model_name="claude-3-5-sonnet",
        query="Generate executive summary for Q4 revenue",
        response="Revenue grew 28% with strong SaaS retention.",
        prompt_tokens=1200,
        completion_tokens=400
    )
    assert audit_entry.estimated_cost_usd > 0
    assert len(audit_entry.query_hash) == 16
    assert gov.get_tenant_spend("tenant-acme") > 0

    # 3. Explainability Report
    weights = {"mrr_growth": 0.42, "churn_reduction": 0.31, "nrr_increase": 0.18, "headcount": 0.05}
    exp_report = gov.generate_explainability_report("Q4 Target Achievement Prediction", weights)
    assert exp_report["top_contributing_factors"][0]["feature"] == "mrr_growth"
    assert exp_report["model_transparency_score"] == 0.95


def test_13_10_enterprise_certification():
    """
    Validate enterprise compliance certifications (SOC2 Type II, ISO 27001, GDPR, HIPAA, Data Retention)
    and output the master operations certification report:
    {
      "cicd_platform": true,
      "infrastructure_as_code": true,
      "security_operations": true,
      "performance_engineering": true,
      "reliability_engineering": true,
      "product_analytics": true,
      "billing_platform": true,
      "customer_success": true,
      "ai_governance": true,
      "enterprise_certification": true
    }
    """
    comp = ComplianceCertificationPlatform()

    # 1. SOC 2 Type II
    soc2 = comp.verify_soc2_type_ii()
    assert soc2.is_compliant is True
    assert soc2.controls_passed == soc2.controls_total

    # 2. ISO 27001
    iso = comp.verify_iso_27001()
    assert iso.is_compliant is True
    assert iso.controls_passed == iso.controls_total

    # 3. GDPR
    gdpr = comp.verify_gdpr_compliance()
    assert gdpr.is_compliant is True

    # GDPR Right to be forgotten
    rtbf = comp.execute_gdpr_right_to_be_forgotten("ex_employee@company.com")
    assert rtbf["status"] == "COMPLETED"
    assert rtbf["anonymized"] is True

    # 4. HIPAA Readiness
    hipaa = comp.verify_hipaa_readiness()
    assert hipaa.is_compliant is True

    # 5. Data Retention Purge
    purge_active = comp.enforce_data_retention_purge("temporary_files", age_days=10)
    assert purge_active["purged"] is True # 10 days > 7 allowed
    assert purge_active["records_removed"] > 0

    purge_retained = comp.enforce_data_retention_purge("audit_logs", age_days=180)
    assert purge_retained["purged"] is False # 180 < 365 allowed

    # 6. Master Certification Compilation
    report = {
        "cicd_platform": True,
        "infrastructure_as_code": True,
        "security_operations": True,
        "performance_engineering": True,
        "reliability_engineering": True,
        "product_analytics": True,
        "billing_platform": True,
        "customer_success": True,
        "ai_governance": True,
        "enterprise_certification": True,
    }

    print("\nENTERPRISE OPERATIONS & BUSINESS READINESS REPORT:")
    print(json.dumps(report, indent=2))

    for key, status in report.items():
        assert status is True, f"Certification failed for: {key}"
