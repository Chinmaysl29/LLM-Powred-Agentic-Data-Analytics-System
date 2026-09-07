"""Service for Phase 3.6 Statistics Agent.

Performs inferential statistics, hypothesis testing, regression analysis,
correlation significance, confidence intervals, chi-square testing,
statistical significance evaluation, and root cause detection.
"""

import logging
import time
from typing import Any
import numpy as np
import pandas as pd
from scipy import stats
from fastapi import Depends

from backend.app.core.exceptions import DataRetrievalError
from backend.app.schemas.statistics import (
    ChiSquareResult,
    ConfidenceInterval,
    DescriptiveProfile,
    HypothesisTestResult,
    Percentiles,
    Quartiles,
    RegressionDriver,
    RegressionResult,
    RootCauseItem,
    SignificantRelationship,
    SignificanceLevel,
    StatisticsBusinessInsight,
    StatisticsResults,
)
from backend.app.services.data_retrieval_service import (
    DataRetrievalService,
    get_data_retrieval_service,
)

logger = logging.getLogger(__name__)


class StatisticsService:
    """Core analytical service for statistical inference and hypothesis testing."""

    def __init__(self, retrieval_service: DataRetrievalService | None = None) -> None:
        self._retrieval_service = retrieval_service

    def analyze_dataframe(
        self,
        df: pd.DataFrame,
        dataset_id: str | None = None,
        target_column: str | None = None,
    ) -> StatisticsResults:
        """Execute complete inferential statistical analysis on a DataFrame."""
        start_time = time.perf_counter()
        logger.info("Starting Statistics Agent analysis for dataset_id=%s, shape=%s", dataset_id, df.shape)

        if df.empty:
            logger.warning("Empty dataframe provided to StatisticsService")
            return self._build_empty_results()

        # Identify column types
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = [c for c in df.columns if c not in numeric_cols]

        # 1. Descriptive Statistics
        descriptive_stats = self._calculate_descriptive_statistics(df, numeric_cols)

        # 2. Hypothesis Testing (T-test, Paired T-test, ANOVA)
        hypothesis_tests = self._perform_hypothesis_tests(df, numeric_cols, categorical_cols)

        # 3. Correlation Significance
        correlations, sig_relationships_from_corr = self._analyze_correlation_significance(df, numeric_cols)

        # 4. Regression Analysis & Driver Discovery
        regression_results = self._perform_regression_analysis(df, numeric_cols, target_column)

        # 5. Confidence Intervals (95% and 99%)
        confidence_intervals = self._calculate_confidence_intervals(df, numeric_cols)

        # 6. Chi-Square Tests of Independence
        chi_square_results = self._perform_chi_square_tests(df, categorical_cols)

        # 7. Aggregate Significant Relationships
        significant_relationships = self._compile_significant_relationships(
            correlations_sig=sig_relationships_from_corr,
            hypothesis_tests=hypothesis_tests,
            regression_results=regression_results,
            chi_square_results=chi_square_results,
        )

        # 8. Root Cause Detection
        root_causes = self._detect_root_causes(regression_results, hypothesis_tests)

        # 9. Business Insight Generation
        business_insights = self._generate_business_insights(
            descriptive=descriptive_stats,
            hypothesis_tests=hypothesis_tests,
            regression_results=regression_results,
            confidence_intervals=confidence_intervals,
            chi_square_results=chi_square_results,
            root_causes=root_causes,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Completed Statistics Agent analysis for dataset_id=%s in %.2fms (insights=%d, root_causes=%d)",
            dataset_id, duration_ms, len(business_insights), len(root_causes)
        )

        return StatisticsResults(
            descriptive_statistics=descriptive_stats,
            hypothesis_tests=hypothesis_tests,
            regression_results=regression_results,
            confidence_intervals=confidence_intervals,
            chi_square_results=chi_square_results,
            significant_relationships=significant_relationships,
            root_causes=root_causes,
            business_insights=business_insights,
        )

    async def analyze_dataset(
        self,
        dataset_id: str,
        version_number: int | None = None,
        target_column: str | None = None,
        sample_size: int | None = None,
    ) -> StatisticsResults:
        """Load dataset from retrieval service and execute statistical analysis."""
        if not self._retrieval_service:
            raise DataRetrievalError("DataRetrievalService not injected into StatisticsService")

        logger.info("Retrieving dataset %s (version=%s) for statistical analysis", dataset_id, version_number)
        df, _ = self._retrieval_service.load_dataframe(
            dataset_id=dataset_id,
            version_number=version_number,
            sample_size=sample_size,
        )

        return self.analyze_dataframe(df, dataset_id=dataset_id, target_column=target_column)

    # -------------------------------------------------------------------------
    # 1. Descriptive Statistics
    # -------------------------------------------------------------------------

    def _calculate_descriptive_statistics(
        self, df: pd.DataFrame, numeric_cols: list[str]
    ) -> dict[str, DescriptiveProfile]:
        """Generate deep parametric and percentile-based descriptive summaries."""
        profiles: dict[str, DescriptiveProfile] = {}

        for col in numeric_cols:
            s = df[col].dropna()
            if s.empty:
                continue

            count = int(s.count())
            mean = float(s.mean())
            median = float(s.median())
            mode_series = s.mode()
            mode_val = float(mode_series.iloc[0]) if not mode_series.empty else None
            variance = float(s.var(ddof=1)) if count > 1 else 0.0
            std_dev = float(s.std(ddof=1)) if count > 1 else 0.0
            min_val = float(s.min())
            max_val = float(s.max())
            range_val = max_val - min_val

            q1 = float(s.quantile(0.25))
            q2 = median
            q3 = float(s.quantile(0.75))
            iqr = q3 - q1

            percentiles = Percentiles(
                p5=round(float(s.quantile(0.05)), 4),
                p10=round(float(s.quantile(0.10)), 4),
                p25=round(q1, 4),
                p50=round(q2, 4),
                p75=round(q3, 4),
                p90=round(float(s.quantile(0.90)), 4),
                p95=round(float(s.quantile(0.95)), 4),
            )

            quartiles = Quartiles(
                q1=round(q1, 4),
                q2=round(q2, 4),
                q3=round(q3, 4),
                iqr=round(iqr, 4),
            )

            profiles[col] = DescriptiveProfile(
                count=count,
                mean=round(mean, 4),
                median=round(median, 4),
                mode=round(mode_val, 4) if mode_val is not None else None,
                variance=round(variance, 4),
                std_dev=round(std_dev, 4),
                range_val=round(range_val, 4),
                min=round(min_val, 4),
                max=round(max_val, 4),
                quartiles=quartiles,
                percentiles=percentiles,
            )

        return profiles

    # -------------------------------------------------------------------------
    # 2. Hypothesis Testing
    # -------------------------------------------------------------------------

    def _perform_hypothesis_tests(
        self,
        df: pd.DataFrame,
        numeric_cols: list[str],
        categorical_cols: list[str],
    ) -> dict[str, list[HypothesisTestResult]]:
        """Run two-sample t-tests, paired t-tests, and one-way ANOVA across available columns."""
        test_results: dict[str, list[HypothesisTestResult]] = {
            "two_sample_ttest": [],
            "paired_ttest": [],
            "one_way_anova": [],
        }

        # 1. Independent Two-Sample T-Test (for categories with exactly 2 values)
        for cat_col in categorical_cols[:5]:
            unique_vals = df[cat_col].dropna().unique()
            if len(unique_vals) == 2:
                g1_name, g2_name = str(unique_vals[0]), str(unique_vals[1])
                for num_col in numeric_cols[:4]:
                    s1 = df[df[cat_col] == unique_vals[0]][num_col].dropna()
                    s2 = df[df[cat_col] == unique_vals[1]][num_col].dropna()
                    if len(s1) >= 3 and len(s2) >= 3:
                        try:
                            t_stat, p_val = stats.ttest_ind(s1, s2, equal_var=False)
                            if pd.notna(p_val):
                                sig_tier = self.classify_significance(p_val)
                                df_val = float(len(s1) + len(s2) - 2)
                                reject = p_val < 0.05
                                diff = s1.mean() - s2.mean()
                                interp = (
                                    f"Statistically significant difference detected in {num_col} between "
                                    f"{cat_col} '{g1_name}' (mean={s1.mean():.2f}) and '{g2_name}' (mean={s2.mean():.2f})."
                                    if reject else
                                    f"No statistically significant difference in {num_col} between '{g1_name}' and '{g2_name}'."
                                )
                                test_results["two_sample_ttest"].append(
                                    HypothesisTestResult(
                                        test_name=f"Two-Sample Welch's T-Test ({cat_col})",
                                        test_type="two_sample_ttest",
                                        variable=num_col,
                                        group_a=f"{cat_col}={g1_name}",
                                        group_b=f"{cat_col}={g2_name}",
                                        statistic=round(float(t_stat), 4),
                                        p_value=round(float(p_val), 6),
                                        degrees_of_freedom=round(df_val, 1),
                                        significance_tier=sig_tier,
                                        null_hypothesis_rejected=reject,
                                        interpretation=interp,
                                    )
                                )
                        except Exception as e:
                            logger.debug("T-test failed for %s on %s: %s", num_col, cat_col, e)

        # 2. Paired T-Test (between correlated numeric columns)
        if len(numeric_cols) >= 2:
            for i in range(min(3, len(numeric_cols))):
                for j in range(i + 1, min(4, len(numeric_cols))):
                    col_a = numeric_cols[i]
                    col_b = numeric_cols[j]
                    valid = df[[col_a, col_b]].dropna()
                    if len(valid) >= 5:
                        try:
                            t_stat, p_val = stats.ttest_rel(valid[col_a], valid[col_b])
                            if pd.notna(p_val):
                                sig_tier = self.classify_significance(p_val)
                                reject = p_val < 0.05
                                interp = (
                                    f"Statistically significant difference between paired measures {col_a} and {col_b} (p={p_val:.4f})."
                                    if reject else
                                    f"No significant paired difference between {col_a} and {col_b}."
                                )
                                test_results["paired_ttest"].append(
                                    HypothesisTestResult(
                                        test_name=f"Paired T-Test ({col_a} vs {col_b})",
                                        test_type="paired_ttest",
                                        variable=f"{col_a} vs {col_b}",
                                        group_a=col_a,
                                        group_b=col_b,
                                        statistic=round(float(t_stat), 4),
                                        p_value=round(float(p_val), 6),
                                        degrees_of_freedom=float(len(valid) - 1),
                                        significance_tier=sig_tier,
                                        null_hypothesis_rejected=reject,
                                        interpretation=interp,
                                    )
                                )
                        except Exception as e:
                            logger.debug("Paired t-test failed for %s vs %s: %s", col_a, col_b, e)

        # 3. One-Way ANOVA (for categories with 3 to 8 unique values)
        for cat_col in categorical_cols[:5]:
            unique_vals = df[cat_col].dropna().unique()
            if 3 <= len(unique_vals) <= 8:
                for num_col in numeric_cols[:4]:
                    groups = [
                        df[df[cat_col] == val][num_col].dropna().values
                        for val in unique_vals
                    ]
                    # Ensure each group has at least 3 samples
                    if all(len(g) >= 3 for g in groups):
                        try:
                            f_stat, p_val = stats.f_oneway(*groups)
                            if pd.notna(p_val):
                                sig_tier = self.classify_significance(p_val)
                                reject = p_val < 0.05
                                interp = (
                                    f"Statistically significant variance in {num_col} across {cat_col} groups (F={f_stat:.2f}, p={p_val:.4f})."
                                    if reject else
                                    f"No significant variance in {num_col} across {cat_col} groups."
                                )
                                test_results["one_way_anova"].append(
                                    HypothesisTestResult(
                                        test_name=f"One-Way ANOVA ({cat_col})",
                                        test_type="one_way_anova",
                                        variable=num_col,
                                        group_a=f"{cat_col} ({len(unique_vals)} groups)",
                                        group_b=None,
                                        statistic=round(float(f_stat), 4),
                                        p_value=round(float(p_val), 6),
                                        degrees_of_freedom=float(len(unique_vals) - 1),
                                        significance_tier=sig_tier,
                                        null_hypothesis_rejected=reject,
                                        interpretation=interp,
                                    )
                                )
                        except Exception as e:
                            logger.debug("ANOVA failed for %s on %s: %s", num_col, cat_col, e)

        return test_results

    # -------------------------------------------------------------------------
    # 3. Correlation Significance
    # -------------------------------------------------------------------------

    def _analyze_correlation_significance(
        self, df: pd.DataFrame, numeric_cols: list[str]
    ) -> tuple[dict[str, Any], list[SignificantRelationship]]:
        """Compute Pearson correlations with exact two-tailed p-values and confidence levels."""
        correlations: dict[str, Any] = {}
        significant_relationships: list[SignificantRelationship] = []

        if len(numeric_cols) < 2:
            return correlations, significant_relationships

        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                col_a = numeric_cols[i]
                col_b = numeric_cols[j]
                clean = df[[col_a, col_b]].dropna()
                if len(clean) >= 5:
                    try:
                        r, p_val = stats.pearsonr(clean[col_a], clean[col_b])
                        if pd.notna(r) and pd.notna(p_val):
                            sig_tier = self.classify_significance(p_val)
                            correlations[f"{col_a}:{col_b}"] = {
                                "correlation": round(float(r), 4),
                                "p_value": round(float(p_val), 6),
                                "significance": sig_tier,
                            }
                            # If correlation is notable (|r| >= 0.4) and significant
                            if abs(r) >= 0.4 and p_val < 0.05:
                                direction = "positive" if r > 0 else "negative"
                                significant_relationships.append(
                                    SignificantRelationship(
                                        source_variable=col_a,
                                        target_variable=col_b,
                                        relationship_type="correlation",
                                        metric_value=round(float(r), 4),
                                        p_value=round(float(p_val), 6),
                                        significance_tier=sig_tier,
                                        insight=(
                                            f"Statistically verified {direction} correlation (r={r:.2f}, p={p_val:.4f}). "
                                            f"Changes in {col_a} are significantly linked with changes in {col_b}."
                                        ),
                                    )
                                )
                    except Exception as e:
                        logger.debug("Correlation failed for %s and %s: %s", col_a, col_b, e)

        return correlations, significant_relationships

    # -------------------------------------------------------------------------
    # 4. Regression Analysis
    # -------------------------------------------------------------------------

    def _perform_regression_analysis(
        self,
        df: pd.DataFrame,
        numeric_cols: list[str],
        target_column: str | None = None,
    ) -> dict[str, RegressionResult]:
        """Perform simple and multiple linear regression with standardized beta importance."""
        results: dict[str, RegressionResult] = {}

        if len(numeric_cols) < 2:
            return results

        # Determine target variable: use requested target or infer from sales/revenue keywords
        chosen_target = target_column
        if not chosen_target or chosen_target not in numeric_cols:
            for priority_keyword in ["revenue", "sales", "profit", "amount", "target", "spend", "cost"]:
                match = next((c for c in numeric_cols if priority_keyword in c.lower()), None)
                if match:
                    chosen_target = match
                    break
            if not chosen_target:
                chosen_target = numeric_cols[0]

        predictors = [c for c in numeric_cols if c != chosen_target][:6]  # Limit to 6 predictors
        if not predictors:
            return results

        clean_df = df[[chosen_target] + predictors].dropna()
        n = len(clean_df)
        k = len(predictors)

        if n <= k + 2:
            return results

        try:
            Y = clean_df[chosen_target].values
            X = clean_df[predictors].values

            # Add intercept column
            X_aug = np.column_stack([np.ones(n), X])

            # Solve OLS via least squares
            params, residuals, rank, s = np.linalg.lstsq(X_aug, Y, rcond=None)
            intercept = float(params[0])
            coefs = params[1:]

            # Predictions & sums of squares
            Y_pred = X_aug @ params
            ss_tot = float(np.sum((Y - np.mean(Y)) ** 2))
            ss_res = float(np.sum((Y - Y_pred) ** 2))

            r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            r_squared = max(0.0, min(1.0, r_squared))

            adj_r_squared = 1.0 - (1.0 - r_squared) * (n - 1) / (n - k - 1) if n > k + 1 else r_squared

            # Degrees of freedom and F-statistic
            df_model = k
            df_resid = n - k - 1
            ms_model = (ss_tot - ss_res) / df_model if df_model > 0 else 0.0
            ms_resid = ss_res / df_resid if df_resid > 0 else 0.0

            if ms_resid > 0:
                f_stat = ms_model / ms_resid
                model_p_val = float(1.0 - stats.f.cdf(f_stat, df_model, df_resid))
            else:
                f_stat = 0.0
                model_p_val = 1.0

            # Compute standard errors for coefficients with pseudo-inverse for numerical stability
            try:
                cov_matrix = np.linalg.pinv(X_aug.T @ X_aug) * ms_resid
                diag_cov = np.maximum(0.0, np.diagonal(cov_matrix))
                std_errors = np.sqrt(diag_cov)[1:]
            except Exception:
                std_errors = np.ones(k)

            # Standardized beta coefficients (Beta = b * (std(X) / std(Y)))
            std_y = np.std(Y, ddof=1) if n > 1 else 1.0
            drivers: list[RegressionDriver] = []

            for idx, feature in enumerate(predictors):
                coef = float(coefs[idx])
                se = float(std_errors[idx]) if idx < len(std_errors) else 1.0
                t_stat = coef / se if se > 0 else 0.0
                p_val = float(2.0 * (1.0 - stats.t.cdf(abs(t_stat), df=df_resid))) if df_resid > 0 else 1.0

                std_x = float(np.std(clean_df[feature].values, ddof=1)) if n > 1 else 1.0
                std_beta = coef * (std_x / std_y) if std_y > 0 else coef

                drivers.append(
                    RegressionDriver(
                        feature=feature,
                        coefficient=round(coef, 4),
                        standardized_coefficient=round(float(std_beta), 4),
                        t_statistic=round(float(t_stat), 4),
                        p_value=round(p_val, 6),
                        importance_rank=0,  # Will rank below
                        is_significant=p_val < 0.05,
                    )
                )

            # Sort drivers by absolute standardized coefficient descending
            drivers.sort(key=lambda d: abs(d.standardized_coefficient), reverse=True)
            for rank_idx, driver in enumerate(drivers):
                driver.importance_rank = rank_idx + 1

            strongest = drivers[0].feature if drivers else None

            summary = (
                f"Multiple regression for {chosen_target} (R² = {r_squared:.2f}, F = {f_stat:.2f}, p = {model_p_val:.4f}). "
                f"Top driver: {strongest} with standardized effect of {drivers[0].standardized_coefficient:.2f}."
                if strongest else f"Regression model fitted with R² = {r_squared:.2f}."
            )

            results[chosen_target] = RegressionResult(
                target_variable=chosen_target,
                predictors=predictors,
                r_squared=round(r_squared, 4),
                adjusted_r_squared=round(adj_r_squared, 4),
                f_statistic=round(float(f_stat), 4),
                p_value=round(model_p_val, 6),
                intercept=round(intercept, 4),
                drivers=drivers,
                strongest_driver=strongest,
                summary=summary,
            )

        except Exception as e:
            logger.error("Regression analysis failed on target %s: %s", chosen_target, e)

        return results

    # -------------------------------------------------------------------------
    # 5. Confidence Intervals
    # -------------------------------------------------------------------------

    def _calculate_confidence_intervals(
        self, df: pd.DataFrame, numeric_cols: list[str]
    ) -> dict[str, dict[str, ConfidenceInterval]]:
        """Calculate 95% and 99% confidence intervals for population means."""
        ci_dict: dict[str, dict[str, ConfidenceInterval]] = {}

        for col in numeric_cols:
            s = df[col].dropna()
            n = len(s)
            if n < 2:
                continue

            mean = float(s.mean())
            std = float(s.std(ddof=1))
            se = std / np.sqrt(n) if n > 0 else 0.0

            ci_dict[col] = {}

            # 95% CI (t-critical for df=n-1, alpha=0.05)
            t_crit_95 = float(stats.t.ppf(0.975, df=n - 1))
            me_95 = t_crit_95 * se
            ci_dict[col]["95%"] = ConfidenceInterval(
                column=col,
                confidence_level="95%",
                mean=round(mean, 4),
                std_error=round(se, 4),
                margin_of_error=round(me_95, 4),
                lower_bound=round(mean - me_95, 4),
                upper_bound=round(mean + me_95, 4),
            )

            # 99% CI (t-critical for df=n-1, alpha=0.01)
            t_crit_99 = float(stats.t.ppf(0.995, df=n - 1))
            me_99 = t_crit_99 * se
            ci_dict[col]["99%"] = ConfidenceInterval(
                column=col,
                confidence_level="99%",
                mean=round(mean, 4),
                std_error=round(se, 4),
                margin_of_error=round(me_99, 4),
                lower_bound=round(mean - me_99, 4),
                upper_bound=round(mean + me_99, 4),
            )

        return ci_dict

    # -------------------------------------------------------------------------
    # 6. Chi-Square Tests of Independence
    # -------------------------------------------------------------------------

    def _perform_chi_square_tests(
        self, df: pd.DataFrame, categorical_cols: list[str]
    ) -> list[ChiSquareResult]:
        """Perform Chi-Square test of independence for pairs of categorical variables."""
        results: list[ChiSquareResult] = []

        if len(categorical_cols) < 2:
            return results

        for i in range(min(4, len(categorical_cols))):
            for j in range(i + 1, min(5, len(categorical_cols))):
                col_a = categorical_cols[i]
                col_b = categorical_cols[j]
                clean = df[[col_a, col_b]].dropna()
                
                # Check cardinality is suitable (2 to 15 unique values)
                n_a = clean[col_a].nunique()
                n_b = clean[col_b].nunique()
                if 2 <= n_a <= 15 and 2 <= n_b <= 15 and len(clean) >= 15:
                    try:
                        table = pd.crosstab(clean[col_a], clean[col_b])
                        chi2, p_val, dof, _ = stats.chi2_contingency(table)
                        if pd.notna(p_val):
                            sig_tier = self.classify_significance(p_val)
                            is_dep = p_val < 0.05
                            interp = (
                                f"Statistically significant association between '{col_a}' and '{col_b}' (χ² = {chi2:.2f}, p = {p_val:.4f}). "
                                f"The distribution of {col_a} is dependent on {col_b}."
                                if is_dep else
                                f"'{col_a}' and '{col_b}' appear statistically independent (p = {p_val:.4f})."
                            )
                            results.append(
                                ChiSquareResult(
                                    variable_a=col_a,
                                    variable_b=col_b,
                                    chi2_statistic=round(float(chi2), 4),
                                    p_value=round(float(p_val), 6),
                                    degrees_of_freedom=int(dof),
                                    is_dependent=is_dep,
                                    significance_tier=sig_tier,
                                    interpretation=interp,
                                )
                            )
                    except Exception as e:
                        logger.debug("Chi-square test failed for %s and %s: %s", col_a, col_b, e)

        return results

    # -------------------------------------------------------------------------
    # 7. Significance Engine Helper
    # -------------------------------------------------------------------------

    @staticmethod
    def classify_significance(p_value: float) -> SignificanceLevel:
        """Classify p-value into standardized significance tiers."""
        if p_value < 0.01:
            return "highly_significant"
        elif p_value < 0.05:
            return "moderately_significant"
        else:
            return "not_significant"

    # -------------------------------------------------------------------------
    # 8. Aggregation & Root Cause Detection
    # -------------------------------------------------------------------------

    def _compile_significant_relationships(
        self,
        correlations_sig: list[SignificantRelationship],
        hypothesis_tests: dict[str, list[HypothesisTestResult]],
        regression_results: dict[str, RegressionResult],
        chi_square_results: list[ChiSquareResult],
    ) -> list[SignificantRelationship]:
        """Aggregate verified relationships meeting statistical significance."""
        all_sig: list[SignificantRelationship] = list(correlations_sig)

        # From regression drivers
        for target, reg in regression_results.items():
            for driver in reg.drivers:
                if driver.is_significant:
                    all_sig.append(
                        SignificantRelationship(
                            source_variable=driver.feature,
                            target_variable=target,
                            relationship_type="regression_driver",
                            metric_value=driver.standardized_coefficient,
                            p_value=driver.p_value,
                            significance_tier=self.classify_significance(driver.p_value),
                            insight=(
                                f"'{driver.feature}' is a statistically verified driver for '{target}' "
                                f"(standardized beta = {driver.standardized_coefficient:.2f}, p = {driver.p_value:.4f})."
                            ),
                        )
                    )

        # From hypothesis tests
        for test_type, tests in hypothesis_tests.items():
            for t in tests:
                if t.null_hypothesis_rejected:
                    all_sig.append(
                        SignificantRelationship(
                            source_variable=t.group_a,
                            target_variable=t.variable,
                            relationship_type="group_difference",
                            metric_value=t.statistic,
                            p_value=t.p_value,
                            significance_tier=t.significance_tier,
                            insight=t.interpretation,
                        )
                    )

        # From chi-square
        for chi in chi_square_results:
            if chi.is_dependent:
                all_sig.append(
                    SignificantRelationship(
                        source_variable=chi.variable_a,
                        target_variable=chi.variable_b,
                        relationship_type="categorical_dependency",
                        metric_value=chi.chi2_statistic,
                        p_value=chi.p_value,
                        significance_tier=chi.significance_tier,
                        insight=chi.interpretation,
                    )
                )

        return all_sig

    def _detect_root_causes(
        self,
        regression_results: dict[str, RegressionResult],
        hypothesis_tests: dict[str, list[HypothesisTestResult]],
    ) -> list[RootCauseItem]:
        """Identify primary drivers and root causes using statistical variance and group weights."""
        root_causes: list[RootCauseItem] = []

        # 1. Driver-based root causes from regression models
        for target, reg in regression_results.items():
            if reg.drivers:
                top_driver = reg.drivers[0]
                if top_driver.is_significant or reg.r_squared >= 0.3:
                    direction = "positive" if top_driver.coefficient > 0 else "negative"
                    pct_explained = round(reg.r_squared * 100.0, 1)
                    evidence = (
                        f"R² = {reg.r_squared:.2f}, standardized beta = {top_driver.standardized_coefficient:.2f}, "
                        f"t = {top_driver.t_statistic:.2f}, p = {top_driver.p_value:.4f}"
                    )
                    takeaway = (
                        f"Changes in '{top_driver.feature}' represent the primary driver explaining {pct_explained}% "
                        f"of variance in '{target}'. A {direction} relationship indicates adjustments here will directly "
                        f"impact overall {target} outcomes."
                    )
                    root_causes.append(
                        RootCauseItem(
                            target_metric=target,
                            primary_driver=top_driver.feature,
                            variance_explained_pct=pct_explained,
                            direction=direction,
                            statistical_evidence=evidence,
                            business_takeaway=takeaway,
                        )
                    )

        # 2. Categorical disparity root causes from hypothesis testing
        for test in hypothesis_tests.get("two_sample_ttest", []):
            if test.null_hypothesis_rejected and abs(test.statistic) > 3.0:
                root_causes.append(
                    RootCauseItem(
                        target_metric=test.variable,
                        primary_driver=test.group_a,
                        variance_explained_pct=round(min(100.0, abs(test.statistic) * 8.0), 1),
                        direction="divergent",
                        statistical_evidence=f"Welch's t = {test.statistic:.2f}, p = {test.p_value:.4f}",
                        business_takeaway=f"Segment disparity in {test.group_a} is a primary driver of overall variance in {test.variable}.",
                    )
                )

        return root_causes

    # -------------------------------------------------------------------------
    # 9. Business Insights Layer
    # -------------------------------------------------------------------------

    def _generate_business_insights(
        self,
        descriptive: dict[str, DescriptiveProfile],
        hypothesis_tests: dict[str, list[HypothesisTestResult]],
        regression_results: dict[str, RegressionResult],
        confidence_intervals: dict[str, dict[str, ConfidenceInterval]],
        chi_square_results: list[ChiSquareResult],
        root_causes: list[RootCauseItem],
    ) -> list[StatisticsBusinessInsight]:
        """Synthesize statistical findings into executive, business-readable takeaways."""
        insights: list[StatisticsBusinessInsight] = []

        # 1. Regression & Primary Driver Insights (Success criteria compliance)
        for target, reg in regression_results.items():
            if reg.drivers:
                top = reg.drivers[0]
                pct_var = int(round(reg.r_squared * 100))
                p_str = "< 0.001" if reg.p_value < 0.001 else f"= {reg.p_value:.4f}"
                insights.append(
                    StatisticsBusinessInsight(
                        category="driver_impact",
                        title=f"{top.feature.replace('_', ' ').title()} as Primary Driver for {target.replace('_', ' ').title()}",
                        insight=(
                            f"{top.feature} explains {pct_var}% of {target} variance and is the most influential growth factor "
                            f"(standardized effect = {top.standardized_coefficient:.2f}, p {p_str})."
                        ),
                        impact="high",
                    )
                )

                # Secondary drivers if significant
                sig_secondary = [d for d in reg.drivers[1:3] if d.is_significant]
                if sig_secondary:
                    sec_names = ", ".join(d.feature for d in sig_secondary)
                    insights.append(
                        StatisticsBusinessInsight(
                            category="secondary_drivers",
                            title=f"Secondary Contributors to {target.replace('_', ' ').title()}",
                            insight=f"Additional statistically significant contributors include {sec_names}.",
                            impact="medium",
                        )
                    )

        # 2. Hypothesis Testing Insights
        for test in hypothesis_tests.get("two_sample_ttest", []):
            if test.null_hypothesis_rejected:
                insights.append(
                    StatisticsBusinessInsight(
                        category="segment_disparity",
                        title="Statistically Significant Segment Disparity",
                        insight=(
                            f"A confirmed performance gap exists in '{test.variable}' across '{test.group_a}' "
                            f"vs '{test.group_b}' (t = {test.statistic:.2f}, p = {test.p_value:.4f})."
                        ),
                        impact="high",
                    )
                )
                break

        for anova in hypothesis_tests.get("one_way_anova", []):
            if anova.null_hypothesis_rejected:
                insights.append(
                    StatisticsBusinessInsight(
                        category="group_variance",
                        title=f"Multi-Group Divergence in {anova.variable.replace('_', ' ').title()}",
                        insight=(
                            f"{anova.variable} exhibits statistically significant variance across {anova.group_a} "
                            f"(F = {anova.statistic:.2f}, p = {anova.p_value:.4f}), indicating performance is not uniform."
                        ),
                        impact="medium",
                    )
                )
                break

        # 3. Confidence Interval Executive Forecast
        for col, ci_set in confidence_intervals.items():
            if "95%" in ci_set and any(k in col.lower() for k in ["revenue", "sales", "profit"]):
                ci95 = ci_set["95%"]
                insights.append(
                    StatisticsBusinessInsight(
                        category="confidence_interval",
                        title=f"95% Confidence Bounds for {col.replace('_', ' ').title()}",
                        insight=(
                            f"With 95% statistical confidence, true population mean for {col} lies between "
                            f"{ci95.lower_bound:,.2f} and {ci95.upper_bound:,.2f} (sample mean: {ci95.mean:,.2f})."
                        ),
                        impact="medium",
                    )
                )
                break

        # 4. Categorical Dependency Insight
        for chi in chi_square_results:
            if chi.is_dependent:
                insights.append(
                    StatisticsBusinessInsight(
                        category="categorical_dependency",
                        title=f"Behavioral Link: {chi.variable_a} ↔ {chi.variable_b}",
                        insight=(
                            f"A statistically verified dependency exists between '{chi.variable_a}' and '{chi.variable_b}' "
                            f"(χ² = {chi.chi2_statistic:.2f}, p = {chi.p_value:.4f}). Segmenting strategies should account for this association."
                        ),
                        impact="medium",
                    )
                )
                break

        return insights

    def _build_empty_results(self) -> StatisticsResults:
        """Fallback empty results when DataFrame is empty."""
        return StatisticsResults(
            descriptive_statistics={},
            hypothesis_tests={"two_sample_ttest": [], "paired_ttest": [], "one_way_anova": []},
            regression_results={},
            confidence_intervals={},
            chi_square_results=[],
            significant_relationships=[],
            root_causes=[],
            business_insights=[
                StatisticsBusinessInsight(
                    category="warning",
                    title="Empty Dataset",
                    insight="No data available to perform statistical tests.",
                    impact="high",
                )
            ],
        )


def get_statistics_service(
    retrieval_service: DataRetrievalService = Depends(get_data_retrieval_service),
) -> StatisticsService:
    """FastAPI dependency provider for StatisticsService."""
    return StatisticsService(retrieval_service=retrieval_service)
