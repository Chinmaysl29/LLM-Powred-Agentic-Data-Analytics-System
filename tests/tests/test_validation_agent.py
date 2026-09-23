"""Unit and integration tests for Phase 3.7 Validation Agent."""

import pytest
from fastapi.testclient import TestClient

from backend.agents.validation_agent import ValidationAgentRunner
from backend.app.main import create_app
from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.validation_service import ValidationService


@pytest.fixture
def validation_service() -> ValidationService:
    return ValidationService()


# -----------------------------------------------------------------------------
# 1. Schema Validation Tests
# -----------------------------------------------------------------------------

def test_schema_validation_valid_and_corrupted(validation_service: ValidationService):
    # Valid correlation matrix
    valid_results = {
        "eda": {
            "correlations": {
                "correlation_matrix": {
                    "sales": {"marketing": 0.92, "sales": 1.0},
                    "marketing": {"sales": 0.92, "marketing": 1.0},
                }
            }
        }
    }
    val_valid = validation_service.validate_results(valid_results)
    assert len(val_valid.errors) == 0
    assert any("Schema Check" in a.check_name and a.status == "passed" for a in val_valid.audit_log)

    # Invalid correlation matrix (string instead of numeric float)
    corrupted_results = {
        "eda": {
            "correlations": {
                "correlation_matrix": {
                    "sales": {"marketing": "high"},
                }
            }
        }
    }
    val_corrupted = validation_service.validate_results(corrupted_results)
    assert len(val_corrupted.errors) >= 1
    assert "non-numeric correlation" in val_corrupted.errors[0]
    assert val_corrupted.validation_status == "FAILED"


# -----------------------------------------------------------------------------
# 2. Numerical Consistency Tests (110% sum failure)
# -----------------------------------------------------------------------------

def test_numerical_consistency_percentage_sum_rule_failure(validation_service: ValidationService):
    # North = 40%, South = 35%, East = 20%, West = 15% -> Total 110%
    results = {
        "eda": {
            "categorical_analysis": {
                "region": {
                    "unique_count": 4,
                    "frequency_distribution": {
                        "North": 40.0,
                        "South": 35.0,
                        "East": 20.0,
                        "West": 15.0,
                    },
                }
            }
        }
    }
    res = validation_service.validate_results(results)
    assert len(res.errors) >= 1
    assert "110.0%" in res.errors[0]
    assert "100% total rule" in res.errors[0]
    assert res.validation_status == "FAILED"


def test_numerical_consistency_valid_percentages_pass(validation_service: ValidationService):
    results = {
        "eda": {
            "categorical_analysis": {
                "region": {
                    "unique_count": 4,
                    "frequency_distribution": {
                        "North": 40.0,
                        "South": 30.0,
                        "East": 20.0,
                        "West": 10.0,
                    },
                }
            }
        }
    }
    res = validation_service.validate_results(results)
    assert len(res.errors) == 0
    assert res.validation_status in ["PASSED", "WARNING"]


def test_numerical_consistency_negative_variance_fails(validation_service: ValidationService):
    results = {
        "eda": {
            "statistics": {
                "revenue": {"variance": -250.0, "std": 50.0}
            }
        }
    }
    res = validation_service.validate_results(results)
    assert len(res.errors) >= 1
    assert "negative variance" in res.errors[0].lower()


# -----------------------------------------------------------------------------
# 3. Data Grounding Tests
# -----------------------------------------------------------------------------

def test_data_grounding_verified_vs_hallucinated(validation_service: ValidationService):
    # Verified insight
    grounded_results = {
        "eda": {
            "trends": {
                "trends": [{"growth_rate_pct": 12.0}]
            },
            "business_insights": [
                {"insight": "Revenue increased 12% across the evaluated timeline."}
            ]
        }
    }
    val_grounded = validation_service.validate_results(grounded_results)
    assert len(val_grounded.warnings) == 0

    # Hallucinated insight claiming 95% without any underlying metric
    hallucinated_results = {
        "eda": {
            "statistics": {"sales": {"mean": 100, "std": 10, "variance": 100, "min": 50, "max": 150}},
            "trends": {"trends": [{"growth_rate_pct": 5.0}]},
            "correlations": {"strongest_correlations": [{"correlation": 0.30}]},
            "business_insights": [
                {"insight": "Customer conversion exploded by 95% this quarter."}
            ]
        }
    }
    val_hallucinated = validation_service.validate_results(hallucinated_results)
    assert any("95.0%" in w and "grounding" in w.lower() for w in val_hallucinated.warnings)


# -----------------------------------------------------------------------------
# 4. Cross-Agent Consistency Tests
# -----------------------------------------------------------------------------

def test_cross_agent_conflict_detected(validation_service: ValidationService):
    results = {
        "eda": {
            "dataset_summary": {"row_count": 5000},
            "correlations": {
                "correlation_matrix": {"spend": {"revenue": 0.92}}
            }
        },
        "statistics": {
            "descriptive_statistics": {
                "revenue": {"count": 4200}  # Conflict: 5000 vs 4200
            },
            "significant_relationships": [
                {
                    "relationship_type": "correlation",
                    "source_variable": "spend",
                    "target_variable": "revenue",
                    "metric_value": 0.45,  # Conflict: 0.92 vs 0.45
                }
            ]
        }
    }
    res = validation_service.validate_results(results)
    assert any("row count" in w.lower() for w in res.warnings)
    assert any("correlation" in w.lower() and "differs" in w.lower() for w in res.warnings)


# -----------------------------------------------------------------------------
# 5. Recommendation Validation Tests
# -----------------------------------------------------------------------------

def test_recommendation_grounding_verified(validation_service: ValidationService):
    # Valid: Marketing recommendation backed by positive regression driver
    valid_results = {
        "statistics": {
            "regression_results": {
                "revenue": {
                    "drivers": [
                        {"feature": "marketing_spend", "is_significant": True, "coefficient": 3.5}
                    ]
                }
            }
        },
        "recommendation": {
            "actionable_recommendations": [
                "Increase marketing spend budget to accelerate quarterly revenue."
            ]
        }
    }
    res_valid = validation_service.validate_results(valid_results)
    assert not any("marketing" in w.lower() and "recommendation" in w.lower() for w in res_valid.warnings)

    # Invalid: Marketing recommendation with zero backing evidence
    invalid_results = {
        "statistics": {"regression_results": {}},
        "eda": {"correlations": {"strongest_correlations": []}},
        "recommendation": {
            "actionable_recommendations": [
                "Increase marketing spend budget drastically."
            ]
        }
    }
    res_invalid = validation_service.validate_results(invalid_results)
    assert any("lacks statistical backing" in w for w in res_invalid.warnings)


# -----------------------------------------------------------------------------
# 6. Forecast Validation Tests
# -----------------------------------------------------------------------------

def test_forecast_validation_inverted_ci_fails(validation_service: ValidationService):
    results = {
        "forecasting": {
            "confidence_interval": [500.0, 100.0]  # Lower > Upper is invalid
        }
    }
    res = validation_service.validate_results(results)
    assert len(res.errors) >= 1
    assert "lower bound (500.0) > upper bound (100.0)" in res.errors[0]


def test_forecast_validation_explosive_growth_warns(validation_service: ValidationService):
    results = {
        "forecasting": {
            "current_value": 10000000,   # 10M
            "projected_value": 500000000, # 500M (50x)
            "confidence_interval": [400000000, 600000000]
        }
    }
    res = validation_service.validate_results(results)
    assert any("explosive forecast" in w.lower() for w in res.warnings)


# -----------------------------------------------------------------------------
# 7. SQL Safety Validation Tests
# -----------------------------------------------------------------------------

def test_sql_validation_safe_queries(validation_service: ValidationService):
    safe_query = "SELECT order_id, revenue FROM active_dataset WHERE revenue > 500 LIMIT 100;"
    check = validation_service.validate_sql(safe_query, allowed_tables=["active_dataset"])
    assert check.is_safe is True
    assert len(check.blocked_keywords) == 0


def test_sql_validation_blocks_destructive_queries(validation_service: ValidationService):
    queries_to_block = [
        "DROP TABLE customers;",
        "DELETE FROM users WHERE active = 0;",
        "TRUNCATE orders;",
        "ALTER TABLE payments DROP COLUMN id;",
        "UPDATE accounts SET balance = 0;",
    ]
    for q in queries_to_block:
        check = validation_service.validate_sql(q)
        assert check.is_safe is False
        assert len(check.blocked_keywords) >= 1
        assert "blocked" in check.message.lower()


def test_sql_validation_disallowed_table(validation_service: ValidationService):
    check = validation_service.validate_sql("SELECT * FROM secret_passwords;", allowed_tables=["sales_data"])
    assert check.is_safe is False
    assert "not in allowed tables" in check.message


# -----------------------------------------------------------------------------
# 8. Visualization Suitability Tests
# -----------------------------------------------------------------------------

def test_visualization_rejects_pie_chart_high_cardinality(validation_service: ValidationService):
    results = {
        "visualization": {
            "primary_chart": {
                "type": "pie",
                "category_count": 500,  # Unsuitable for pie chart
            }
        }
    }
    res = validation_service.validate_results(results)
    assert len(res.errors) >= 1
    assert "pie chart with 500 categories" in res.errors[0].lower()
    assert "recommend bar chart" in res.errors[0].lower()


def test_visualization_accepts_bar_chart(validation_service: ValidationService):
    results = {
        "visualization": {
            "primary_chart": {
                "type": "bar",
                "category_count": 500,
            }
        }
    }
    res = validation_service.validate_results(results)
    assert len(res.errors) == 0


# -----------------------------------------------------------------------------
# 9. Confidence Scoring & Audit Trail Tests
# -----------------------------------------------------------------------------

def test_confidence_scoring_and_audit_trail(validation_service: ValidationService):
    # Clean results -> high score, PASSED
    clean_results = {
        "eda": {
            "statistics": {"sales": {"mean": 100, "std": 10, "variance": 100}},
            "trends": {"trends": [{"growth_rate_pct": 12.0}]},
            "business_insights": [{"insight": "Growth observed at 12%."}],
        }
    }
    res = validation_service.validate_results(clean_results)
    assert res.confidence_score >= 90
    assert res.validation_status == "PASSED"
    assert len(res.audit_log) > 0
    assert all(a.timestamp is not None for a in res.audit_log)


# -----------------------------------------------------------------------------
# 10. Agent Runner and Orchestrator Integration Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validation_agent_runner():
    runner = ValidationAgentRunner()
    context = WorkflowContext(
        request_id="val-req-1",
        query="Validate results",
        intent="data_quality",
        dataset_id="sales-ds",
    )
    # Add prior agent results
    context.add_result("eda", {
        "trends": {"trends": [{"growth_rate_pct": 12.0}]},
        "business_insights": [{"insight": "Revenue increased 12% across the period."}]
    })

    output = await runner.run(context)
    assert "validation_status" in output
    assert "confidence_score" in output
    assert "audit_log" in output
    assert output["validation_status"] == "PASSED"
    assert output["confidence_score"] >= 95


# -----------------------------------------------------------------------------
# 11. API Route Integration Tests
# -----------------------------------------------------------------------------

def test_api_validation_endpoints():
    app = create_app()
    client = TestClient(app)

    # 1. Test /api/v1/validation/validate
    payload = {
        "results": {
            "percentages": {"North": 40.0, "South": 30.0, "East": 30.0}
        },
        "query": "Check numbers",
    }
    resp = client.post("/api/v1/validation/validate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["validation_result"]["validation_status"] == "PASSED"

    # 2. Test /api/v1/validation/validate-sql
    sql_payload = {"sql": "SELECT * FROM sales_data;"}
    resp_sql = client.post("/api/v1/validation/validate-sql", json=sql_payload)
    assert resp_sql.status_code == 200
    sql_data = resp_sql.json()
    assert sql_data["is_safe"] is True

    # 3. Test destructive SQL blocked via API
    bad_sql_payload = {"sql": "DROP TABLE critical_records;"}
    resp_bad = client.post("/api/v1/validation/validate-sql", json=bad_sql_payload)
    assert resp_bad.status_code == 200
    bad_data = resp_bad.json()
    assert bad_data["is_safe"] is False
    assert "DROP" in bad_data["blocked_keywords"]
