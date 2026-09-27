"""Enterprise Chart Selector module.

Intelligently selects the optimal Power BI-grade visualization type based on data
shape, data types, cardinality, and analytical query intent.
Supports: Line, Bar, Area, Treemap, Heatmap, Scatter, KPI Card, Waterfall, Funnel, Pareto.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd


class ChartRecommendation:
    """Encapsulates chart selection recommendation with rationales and axis mappings."""

    def __init__(
        self,
        chart_type: str,
        confidence: float,
        reason: str,
        x_axis: str | None = None,
        y_axis: str | None = None,
        color_by: str | None = None,
        hierarchy: list[str] | None = None,
    ) -> None:
        self.chart_type = chart_type
        self.confidence = confidence
        self.reason = reason
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.color_by = color_by
        self.hierarchy = hierarchy or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "color_by": self.color_by,
            "hierarchy": self.hierarchy,
        }


class ChartSelector:
    """Rule and heuristic selector for Power BI-level chart recommendations."""

    SUPPORTED_CHARTS = [
        "line_chart",
        "bar_chart",
        "area_chart",
        "treemap",
        "heatmap",
        "scatter_plot",
        "kpi_card",
        "waterfall_chart",
        "funnel_chart",
        "pareto_chart",
    ]

    def select_chart(
        self,
        data: list[dict[str, Any]] | pd.DataFrame | None = None,
        query: str = "",
        columns: list[str] | None = None,
        user_intent: str = "",
        **kwargs: Any,
    ) -> ChartRecommendation:
        """Alias accepting data records or DataFrame and user_intent."""
        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data or [])
        q = user_intent or query
        return self.select(df=df, query=q, columns=columns)

    def select(
        self,
        df: pd.DataFrame,
        query: str = "",
        columns: list[str] | None = None,
    ) -> ChartRecommendation:
        """Analyze DataFrame and user query to recommend the best chart type."""
        q = (query or "").lower()
        cols = list(df.columns) if not df.empty else (columns or [])

        # 1. Single number / KPI Card check
        if (len(df) == 1 and len(cols) == 1) or any(k in q for k in ("kpi", "metric", "total only", "summary stat")):
            num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])] if not df.empty else cols
            metric = num_cols[0] if num_cols else (cols[0] if cols else "value")
            return ChartRecommendation(
                chart_type="kpi_card",
                confidence=0.95,
                reason="Single key aggregate metric identified.",
                y_axis=metric,
            )

        # Classify column data types
        numeric_cols: list[str] = []
        datetime_cols: list[str] = []
        categorical_cols: list[str] = []

        if not df.empty:
            for c in cols:
                if pd.api.types.is_numeric_dtype(df[c]):
                    numeric_cols.append(c)
                elif pd.api.types.is_datetime64_any_dtype(df[c]):
                    datetime_cols.append(c)
                else:
                    # Check if string column looks like dates
                    c_lower = c.lower()
                    if any(term in c_lower for term in ("date", "month", "year", "quarter", "day", "time")):
                        datetime_cols.append(c)
                    else:
                        categorical_cols.append(c)
        else:
            # Fallback by column names
            for c in cols:
                c_lower = c.lower()
                if any(term in c_lower for term in ("revenue", "sales", "profit", "amount", "cost", "total", "qty", "count")):
                    numeric_cols.append(c)
                elif any(term in c_lower for term in ("date", "month", "year", "quarter")):
                    datetime_cols.append(c)
                else:
                    categorical_cols.append(c)

        # 2. Query explicit mentions
        if "waterfall" in q or "bridge" in q or ("breakdown" in q and "profit" in q):
            return ChartRecommendation(
                chart_type="waterfall_chart",
                confidence=0.95,
                reason="Query explicitly requests waterfall or cumulative variance breakdown.",
                x_axis=categorical_cols[0] if categorical_cols else (cols[0] if cols else None),
                y_axis=numeric_cols[0] if numeric_cols else None,
            )

        if "funnel" in q or "conversion" in q or "pipeline" in q or "stage" in q:
            return ChartRecommendation(
                chart_type="funnel_chart",
                confidence=0.95,
                reason="Conversion pipeline or sales stages detected.",
                x_axis=categorical_cols[0] if categorical_cols else None,
                y_axis=numeric_cols[0] if numeric_cols else None,
            )

        if "pareto" in q or "80/20" in q:
            return ChartRecommendation(
                chart_type="pareto_chart",
                confidence=0.96,
                reason="Pareto 80/20 cumulative distribution requested.",
                x_axis=categorical_cols[0] if categorical_cols else None,
                y_axis=numeric_cols[0] if numeric_cols else None,
            )

        if "scatter" in q:
            return ChartRecommendation(
                chart_type="scatter_plot",
                confidence=0.95,
                reason="Query requests scatter analysis between continuous metrics.",
                x_axis=numeric_cols[0] if numeric_cols else cols[0],
                y_axis=numeric_cols[1] if len(numeric_cols) > 1 else (numeric_cols[0] if numeric_cols else (cols[1] if len(cols) > 1 else cols[0])),
                color_by=categorical_cols[0] if categorical_cols else None,
            )

        if "heatmap" in q or "correlation matrix" in q or (len(numeric_cols) >= 3 and "correlation" in q):
            return ChartRecommendation(
                chart_type="heatmap",
                confidence=0.92,
                reason="Multi-dimensional density or correlation matrix requested.",
                x_axis=cols[0] if cols else None,
                y_axis=cols[1] if len(cols) > 1 else None,
            )

        if "treemap" in q or "hierarchy" in q:
            return ChartRecommendation(
                chart_type="treemap",
                confidence=0.95,
                reason="Explicit hierarchical treemap requested.",
                x_axis=categorical_cols[0] if categorical_cols else None,
                y_axis=numeric_cols[0] if numeric_cols else None,
                hierarchy=categorical_cols[:2] if len(categorical_cols) >= 2 else categorical_cols,
            )

        # 3. Temporal / Trend Intent or Temporal Dimension -> Line or Area Chart
        is_trend_query = any(term in q for term in ("trend", "month", "monthly", "time", "date", "over time", "history", "annual"))
        if is_trend_query or datetime_cols:
            if "area" in q:
                return ChartRecommendation(
                    chart_type="area_chart",
                    confidence=0.92,
                    reason="Continuous volume trend over time.",
                    x_axis=datetime_cols[0] if datetime_cols else (categorical_cols[0] if categorical_cols else cols[0]),
                    y_axis=numeric_cols[0] if numeric_cols else None,
                )
            return ChartRecommendation(
                chart_type="line_chart",
                confidence=0.94,
                reason="Temporal date dimension with continuous metric ideal for trend visualization.",
                x_axis=datetime_cols[0] if datetime_cols else (categorical_cols[0] if categorical_cols else cols[0]),
                y_axis=numeric_cols[0] if numeric_cols else (cols[1] if len(cols) > 1 else cols[0]),
            )

        # 4. Multi-categorical parts-of-a-whole heuristic -> Treemap
        if len(categorical_cols) >= 2 and numeric_cols:
            return ChartRecommendation(
                chart_type="treemap",
                confidence=0.88,
                reason="Hierarchical parts-of-a-whole breakdown.",
                x_axis=categorical_cols[0],
                y_axis=numeric_cols[0],
                hierarchy=categorical_cols[:2],
            )

        # 4. Categorical comparison -> Bar Chart
        if categorical_cols and numeric_cols:
            return ChartRecommendation(
                chart_type="bar_chart",
                confidence=0.90,
                reason="Discrete categorical comparison across numeric KPI.",
                x_axis=categorical_cols[0],
                y_axis=numeric_cols[0],
            )

        # 5. Default fallback
        x_val = cols[0] if cols else "x"
        y_val = cols[1] if len(cols) > 1 else (numeric_cols[0] if numeric_cols else x_val)
        return ChartRecommendation(
            chart_type="bar_chart",
            confidence=0.75,
            reason="Standard categorical distribution.",
            x_axis=x_val,
            y_axis=y_val,
        )


__all__ = ["ChartSelector", "ChartRecommendation"]
