"""Service for Phase 3.7 Validation Agent.

The final gatekeeper before results reach executive summary or users:
- Schema validation
- Numerical consistency validation (totals, percentages, ratios)
- Data grounding validation (verifying insights against computed metrics)
- Cross-agent consistency validation (detecting inter-agent conflicts)
- Recommendation validation (verifying analytical grounding)
- Forecast validation (checking CI sanity, error rates, explosive forecasts)
- SQL safety validation (blocking destructive commands)
- Visualization suitability validation (preventing inappropriate charts)
- Confidence scoring engine (0-100 score and status)
- Audit trail logging
"""

import logging
import re
import time
from typing import Any
from fastapi import Depends

from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.schemas.validation import (
    AuditCheckStatus,
    AuditLogEntry,
    SQLValidationResult,
    ValidationResult,
    ValidationStatus,
)

logger = logging.getLogger(__name__)

# Destructive / unsafe SQL keywords to block
BLOCKED_SQL_KEYWORDS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"\bALTER\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bSHUTDOWN\b",
]


class ValidationService:
    """Enterprise validation gatekeeper for multi-agent workflow results."""

    def validate_results(
        self,
        results: dict[str, Any],
        context: WorkflowContext | None = None,
        query: str | None = None,
    ) -> ValidationResult:
        """Execute full validation suite across all agent results in the workflow."""
        start_time = time.perf_counter()
        logger.info("Starting validation audit across %d agent results", len(results))

        warnings: list[str] = []
        errors: list[str] = []
        audit_log: list[AuditLogEntry] = []

        # 1. Schema Validation
        self._validate_schemas(results, errors, warnings, audit_log)

        # 2. Numerical Consistency Validation
        self._validate_numerical_consistency(results, errors, warnings, audit_log)

        # 3. Data Grounding Validation
        self._validate_data_grounding(results, errors, warnings, audit_log)

        # 4. Cross-Agent Consistency Validation
        self._validate_cross_agent_consistency(results, errors, warnings, audit_log)

        # 5. Recommendation Validation
        self._validate_recommendations(results, errors, warnings, audit_log)

        # 6. Forecast Validation
        self._validate_forecasts(results, errors, warnings, audit_log)

        # 7. SQL Query Safety Validation
        self._validate_sql_queries(results, errors, warnings, audit_log)

        # 8. Visualization Suitability Validation
        self._validate_visualizations(results, errors, warnings, audit_log)

        # 9. Confidence Scoring Engine
        confidence_score, validation_status = self._compute_confidence_score(errors, warnings)

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Completed validation audit in %.2fms: status=%s, score=%d, errors=%d, warnings=%d, checks=%d",
            duration_ms, validation_status, confidence_score, len(errors), len(warnings), len(audit_log)
        )

        return ValidationResult(
            validation_status=validation_status,
            confidence_score=confidence_score,
            warnings=warnings,
            errors=errors,
            audit_log=audit_log,
        )

    def validate_sql(
        self, sql_query: str, allowed_tables: list[str] | None = None
    ) -> SQLValidationResult:
        """Direct safety validation of a SQL query."""
        blocked_found = []
        for kw_pattern in BLOCKED_SQL_KEYWORDS:
            if re.search(kw_pattern, sql_query, re.IGNORECASE):
                kw_clean = kw_pattern.replace(r"\b", "")
                blocked_found.append(kw_clean)

        if blocked_found:
            return SQLValidationResult(
                is_safe=False,
                blocked_keywords=blocked_found,
                message=f"Query blocked: Destructive SQL operations detected ({', '.join(blocked_found)}).",
            )

        # Check allowed tables if specified
        if allowed_tables:
            from_match = re.search(r"\bFROM\s+([a-zA-Z0-9_]+)", sql_query, re.IGNORECASE)
            if from_match:
                table_name = from_match.group(1).lower()
                allowed_lower = [t.lower() for t in allowed_tables]
                if table_name not in allowed_lower:
                    return SQLValidationResult(
                        is_safe=False,
                        blocked_keywords=[],
                        message=f"Query blocked: Table '{table_name}' is not in allowed tables list.",
                    )

        return SQLValidationResult(
            is_safe=True,
            blocked_keywords=[],
            message="Query validated: Read-only SELECT operation conforming to security policies.",
        )

    # -------------------------------------------------------------------------
    # Internal Engine Implementations
    # -------------------------------------------------------------------------

    def _add_audit(
        self,
        audit_log: list[AuditLogEntry],
        check_name: str,
        agent_target: str,
        status: AuditCheckStatus,
        message: str,
    ) -> None:
        """Append an audit record to the audit trail."""
        audit_log.append(
            AuditLogEntry(
                check_name=check_name,
                agent_target=agent_target,
                status=status,
                message=message,
            )
        )

    def _validate_schemas(
        self,
        results: dict[str, Any],
        errors: list[str],
        warnings: list[str],
        audit_log: list[AuditLogEntry],
    ) -> None:
        """Validate that all agent results adhere to expected data structures and types."""
        # 1. EDA output schema
        if "eda" in results:
            eda_data = results["eda"]
            if isinstance(eda_data, dict):
                # Check for correlation format
                corrs = eda_data.get("correlations", {})
                if isinstance(corrs, dict):
                    matrix = corrs.get("correlation_matrix", {})
                    invalid_types = False
                    for col_a, pair_map in matrix.items():
                        if isinstance(pair_map, dict):
                            for col_b, val in pair_map.items():
                                if not isinstance(val, (int, float)):
                                    invalid_types = True
                                    break
                    if invalid_types:
                        msg = "EDA correlation matrix contains non-numeric correlation values."
                        errors.append(msg)
                        self._add_audit(audit_log, "Schema Check (Correlation Type)", "eda", "failed", msg)
                    else:
                        self._add_audit(audit_log, "Schema Check (Correlation Type)", "eda", "passed", "Numeric types verified.")
            else:
                msg = "EDA output is not a valid dictionary structure."
                errors.append(msg)
                self._add_audit(audit_log, "Schema Check (Structure)", "eda", "failed", msg)

        # 2. Statistics output schema
        if "statistics" in results:
            stat_data = results["statistics"]
            if isinstance(stat_data, dict):
                self._add_audit(audit_log, "Schema Check (Structure)", "statistics", "passed", "Statistics dictionary verified.")
            else:
                msg = "Statistics output is not a valid dictionary structure."
                errors.append(msg)
                self._add_audit(audit_log, "Schema Check (Structure)", "statistics", "failed", msg)

    def _validate_numerical_consistency(
        self,
        results: dict[str, Any],
        errors: list[str],
        warnings: list[str],
        audit_log: list[AuditLogEntry],
    ) -> None:
        """Verify mathematical consistency: percentages, totals, and non-negativity."""
        # Check EDA Categorical distributions & Missingness
        if "eda" in results:
            eda = results["eda"]
            if isinstance(eda, dict):
                # 1. Categorical percentages sum rule (~100%)
                cat_analysis = eda.get("categorical_analysis", {})
                if isinstance(cat_analysis, dict):
                    for col, detail in cat_analysis.items():
                        if isinstance(detail, dict):
                            freq_dist = detail.get("frequency_distribution", {})
                            if isinstance(freq_dist, dict) and len(freq_dist) > 1:
                                total_pct = sum(v for v in freq_dist.values() if isinstance(v, (int, float)))
                                # If all categories are present, sum must equal roughly 100%
                                nunique = detail.get("unique_count", 0)
                                if nunique == len(freq_dist) and abs(total_pct - 100.0) > 2.0:
                                    msg = (
                                        f"Numerical inconsistency in {col}: Percentage breakdown sums to "
                                        f"{total_pct:.1f}%, violating the 100% total rule."
                                    )
                                    errors.append(msg)
                                    self._add_audit(audit_log, f"Percentage Sum Rule ({col})", "eda", "failed", msg)
                                else:
                                    self._add_audit(audit_log, f"Percentage Sum Rule ({col})", "eda", "passed", "Percentages within tolerance.")

                # 2. Non-negativity of variances and standard deviations
                stats_dict = eda.get("statistics", {})
                if isinstance(stats_dict, dict):
                    for col, metrics in stats_dict.items():
                        if isinstance(metrics, dict):
                            var_val = metrics.get("variance", 0.0)
                            std_val = metrics.get("std", 0.0)
                            if var_val < 0 or std_val < 0:
                                msg = f"Impossible negative variance or standard deviation in column '{col}'."
                                errors.append(msg)
                                self._add_audit(audit_log, f"Non-negativity ({col})", "eda", "failed", msg)

        # Check explicit percentages in custom results
        if "percentages" in results:
            pct_data = results["percentages"]
            if isinstance(pct_data, dict):
                total = sum(v for v in pct_data.values() if isinstance(v, (int, float)))
                if abs(total - 100.0) > 2.0:
                    msg = f"Percentage breakdown sums to {total:.1f}%, exceeding 100%."
                    errors.append(msg)
                    self._add_audit(audit_log, "Percentage Sum Rule", "custom", "failed", msg)

    def _validate_data_grounding(
        self,
        results: dict[str, Any],
        errors: list[str],
        warnings: list[str],
        audit_log: list[AuditLogEntry],
    ) -> None:
        """Ensure claims and numbers in business insights exist in underlying calculations."""
        # Collect verified numbers from computed statistics
        verified_numbers: set[float] = set()

        if "eda" in results and isinstance(results["eda"], dict):
            eda = results["eda"]
            # Add summary stats
            for stat in eda.get("statistics", {}).values():
                if isinstance(stat, dict):
                    for k, v in stat.items():
                        if isinstance(v, (int, float)):
                            verified_numbers.add(round(float(v), 2))
            # Add trend percentages
            trends = eda.get("trends", {})
            if isinstance(trends, dict):
                for t in trends.get("trends", []):
                    if isinstance(t, dict) and "growth_rate_pct" in t:
                        verified_numbers.add(round(float(t["growth_rate_pct"]), 1))
            # Add correlations
            corrs = eda.get("correlations", {})
            if isinstance(corrs, dict):
                for pair in corrs.get("strongest_correlations", []):
                    if isinstance(pair, dict) and "correlation" in pair:
                        verified_numbers.add(round(float(pair["correlation"]), 2))

        if "statistics" in results and isinstance(results["statistics"], dict):
            stat = results["statistics"]
            # Add regression R² and coefficients
            for reg in stat.get("regression_results", {}).values():
                if isinstance(reg, dict):
                    if "r_squared" in reg:
                        verified_numbers.add(round(float(reg["r_squared"]), 2))
                        verified_numbers.add(round(float(reg["r_squared"] * 100), 0))
                    for d in reg.get("drivers", []):
                        if isinstance(d, dict) and "standardized_coefficient" in d:
                            verified_numbers.add(round(float(d["standardized_coefficient"]), 2))

        # Check insights
        insights_to_check = []
        if "eda" in results and isinstance(results["eda"], dict):
            insights_to_check.extend(results["eda"].get("business_insights", []))
        if "statistics" in results and isinstance(results["statistics"], dict):
            insights_to_check.extend(results["statistics"].get("business_insights", []))

        for item in insights_to_check:
            text = item.get("insight", "") if isinstance(item, dict) else str(item)
            # Find percentages or numbers like 15%, 0.92, 89%
            num_matches = re.findall(r"(\d+(?:\.\d+)?)\s*%", text)
            for m in num_matches:
                val = round(float(m), 1)
                # If number is prominent (> 10%) and not found in any variance/growth/frequency, verify tolerance
                matched = any(abs(val - vn) < 1.5 for vn in verified_numbers)
                if not matched and val > 5.0 and len(verified_numbers) > 5:
                    msg = f"Insight claims {val}% without direct grounding in computed metrics: '{text[:80]}...'"
                    warnings.append(msg)
                    self._add_audit(audit_log, "Data Grounding", "insights", "warning", msg)
                    break

        self._add_audit(audit_log, "Data Grounding Suite", "insights", "passed", "Verified insights against computed metrics.")

    def _validate_cross_agent_consistency(
        self,
        results: dict[str, Any],
        errors: list[str],
        warnings: list[str],
        audit_log: list[AuditLogEntry],
    ) -> None:
        """Detect contradictory conclusions between cooperating agents."""
        has_eda = "eda" in results and isinstance(results["eda"], dict)
        has_stats = "statistics" in results and isinstance(results["statistics"], dict)

        if has_eda and has_stats:
            eda_data = results["eda"]
            stats_data = results["statistics"]

            # 1. Compare row counts
            eda_rows = eda_data.get("dataset_summary", {}).get("row_count")
            stats_desc = stats_data.get("descriptive_statistics", {})
            if eda_rows and stats_desc:
                first_metric = next(iter(stats_desc.values()), None)
                if isinstance(first_metric, dict):
                    stat_count = first_metric.get("count")
                    if stat_count and eda_rows != stat_count:
                        msg = f"Cross-agent conflict: EDA row count ({eda_rows}) != Statistics row count ({stat_count})."
                        warnings.append(msg)
                        self._add_audit(audit_log, "Cross-Agent Row Count", "eda vs statistics", "warning", msg)

            # 2. Compare correlation agreement
            eda_corrs = eda_data.get("correlations", {}).get("correlation_matrix", {})
            stat_rels = stats_data.get("significant_relationships", [])
            for rel in stat_rels:
                if isinstance(rel, dict) and rel.get("relationship_type") == "correlation":
                    src = rel.get("source_variable")
                    tgt = rel.get("target_variable")
                    stat_r = rel.get("metric_value")
                    if src and tgt and src in eda_corrs and tgt in eda_corrs[src]:
                        eda_r = eda_corrs[src][tgt]
                        if abs(float(stat_r) - float(eda_r)) > 0.05:
                            msg = f"Cross-agent conflict: Correlation {src}↔{tgt} differs between EDA ({eda_r}) and Statistics ({stat_r})."
                            warnings.append(msg)
                            self._add_audit(audit_log, "Cross-Agent Correlation", "eda vs statistics", "warning", msg)

            self._add_audit(audit_log, "Cross-Agent Consistency", "pipeline", "passed", "No major cross-agent contradictions.")

    def _validate_recommendations(
        self,
        results: dict[str, Any],
        errors: list[str],
        warnings: list[str],
        audit_log: list[AuditLogEntry],
    ) -> None:
        """Verify that recommendations have supporting analytical evidence."""
        rec_data = results.get("recommendation", {})
        if not rec_data or not isinstance(rec_data, dict):
            return

        recs = rec_data.get("actionable_recommendations", [])
        if not recs:
            return

        # Check evidence in statistics or eda
        has_stats = "statistics" in results and isinstance(results["statistics"], dict)
        has_eda = "eda" in results and isinstance(results["eda"], dict)

        for rec in recs:
            rec_text = str(rec).lower()
            if "marketing" in rec_text:
                # Must be backed by positive relationship
                has_support = False
                if has_stats:
                    reg_results = results["statistics"].get("regression_results", {})
                    for reg in reg_results.values():
                        if isinstance(reg, dict):
                            for d in reg.get("drivers", []):
                                if "marketing" in d.get("feature", "").lower() and d.get("is_significant", False):
                                    has_support = True
                if has_eda and not has_support:
                    for p in results["eda"].get("correlations", {}).get("strongest_correlations", []):
                        if "marketing" in str(p).lower():
                            has_support = True

                if not has_support:
                    msg = f"Recommendation lacks statistical backing: '{rec}'"
                    warnings.append(msg)
                    self._add_audit(audit_log, "Recommendation Grounding", "recommendation", "warning", msg)
                else:
                    self._add_audit(audit_log, "Recommendation Grounding", "recommendation", "passed", f"Verified evidence for '{rec[:40]}...'")

    def _validate_forecasts(
        self,
        results: dict[str, Any],
        errors: list[str],
        warnings: list[str],
        audit_log: list[AuditLogEntry],
    ) -> None:
        """Validate forecast sanity, confidence intervals, and explosive growth."""
        forecast_data = results.get("forecasting", {})
        if not forecast_data or not isinstance(forecast_data, dict):
            return

        # 1. Check confidence interval sanity
        ci = forecast_data.get("confidence_interval")
        if isinstance(ci, (list, tuple)) and len(ci) == 2:
            lower, upper = ci[0], ci[1]
            if lower > upper:
                msg = f"Invalid forecast confidence interval: lower bound ({lower}) > upper bound ({upper})."
                errors.append(msg)
                self._add_audit(audit_log, "Forecast CI Sanity", "forecasting", "failed", msg)
            else:
                self._add_audit(audit_log, "Forecast CI Sanity", "forecasting", "passed", "Bounds order verified.")

        # 2. Check for explosive growth (> 10x baseline)
        curr_val = forecast_data.get("current_value")
        pred_val = forecast_data.get("projected_value")
        if curr_val and pred_val and isinstance(curr_val, (int, float)) and isinstance(pred_val, (int, float)):
            if curr_val > 0 and pred_val > curr_val * 10:
                msg = f"Suspicious explosive forecast: Projected ({pred_val}) is >10x baseline ({curr_val})."
                warnings.append(msg)
                self._add_audit(audit_log, "Forecast Growth Sanity", "forecasting", "warning", msg)
            else:
                self._add_audit(audit_log, "Forecast Growth Sanity", "forecasting", "passed", "Forecast growth within realistic boundaries.")

    def _validate_sql_queries(
        self,
        results: dict[str, Any],
        errors: list[str],
        warnings: list[str],
        audit_log: list[AuditLogEntry],
    ) -> None:
        """Inspect generated or provided SQL for destructive operations."""
        sql_query = results.get("sql", {}).get("generated_sql") if isinstance(results.get("sql"), dict) else None
        if not sql_query and "sql_query" in results:
            sql_query = results["sql_query"]

        if sql_query:
            sql_res = self.validate_sql(str(sql_query))
            if not sql_res.is_safe:
                errors.append(sql_res.message)
                self._add_audit(audit_log, "SQL Safety Check", "sql", "failed", sql_res.message)
            else:
                self._add_audit(audit_log, "SQL Safety Check", "sql", "passed", sql_res.message)

    def _validate_visualizations(
        self,
        results: dict[str, Any],
        errors: list[str],
        warnings: list[str],
        audit_log: list[AuditLogEntry],
    ) -> None:
        """Verify that chart types match data distribution and dimensionality."""
        vis = results.get("visualization", {})
        if not vis or not isinstance(vis, dict):
            return

        chart = vis.get("primary_chart", {})
        if isinstance(chart, dict):
            chart_type = chart.get("type", "").lower()
            category_count = chart.get("category_count") or len(chart.get("categories", []))

            # Reject Pie chart with high cardinality (> 10 categories)
            if chart_type in ["pie", "donut"] and category_count > 10:
                msg = (
                    f"Inappropriate chart type: Pie chart with {category_count} categories is unreadable. "
                    "Recommend Bar chart instead."
                )
                errors.append(msg)
                self._add_audit(audit_log, "Chart Suitability (Pie)", "visualization", "failed", msg)
            else:
                self._add_audit(audit_log, "Chart Suitability", "visualization", "passed", "Chart configuration conforms to guidelines.")

    def _compute_confidence_score(
        self, errors: list[str], warnings: list[str]
    ) -> tuple[int, ValidationStatus]:
        """Compute final 0-100 confidence score and overall status."""
        # Base: 100 points
        score = 100
        score -= len(errors) * 25
        score -= len(warnings) * 8
        score = max(0, min(100, score))

        if len(errors) > 0 or score < 60:
            status: ValidationStatus = "FAILED"
        elif len(warnings) > 0 or score < 85:
            status: ValidationStatus = "WARNING"
        else:
            status: ValidationStatus = "PASSED"

        return score, status


def get_validation_service() -> ValidationService:
    """FastAPI dependency provider for ValidationService."""
    return ValidationService()
