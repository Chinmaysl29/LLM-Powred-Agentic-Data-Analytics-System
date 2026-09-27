"""Enterprise Plotly Visualization Engine.

Generates Power BI-grade interactive visualization specs (Plotly JSON + AG Grid schema)
for Line, Bar, Area, Treemap, Heatmap, Scatter, KPI Card, Waterfall, Funnel, and Pareto charts.
Configured with dark slate theme, drilldowns, cross-filtering, interactive tooltips, and exports.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Dark slate theme tokens matching the frontend UI design
THEME_DARK = {
    "paper_bgcolor": "#171b26",
    "plot_bgcolor": "#171b26",
    "font_color": "#f3f4f6",
    "grid_color": "#2d3343",
    "accent_primary": "#3b82f6",
    "accent_secondary": "#10b981",
    "accent_warning": "#f59e0b",
    "accent_danger": "#ef4444",
    "accent_purple": "#8b5cf6",
    "palette": [
        "#3b82f6",
        "#10b981",
        "#f59e0b",
        "#8b5cf6",
        "#ec4899",
        "#06b6d4",
        "#f97316",
        "#14b8a6",
    ],
}


class PlotlyEngine:
    """Builds enterprise Plotly figure specs with Power BI interactivity and AG Grid companions."""

    @staticmethod
    def sample_for_visualization(
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        group_col: str | None = None,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Adaptive sampling helper applying 4-tier enterprise scaling rules."""
        from backend.visualization.generators.adaptive_sampler import get_adaptive_sampling_engine
        return get_adaptive_sampling_engine().sample_data(df, x_col, y_col, group_col)

    @staticmethod
    def _base_layout(title: str, x_label: str = "", y_label: str = "") -> dict[str, Any]:

        return {
            "title": {
                "text": title,
                "font": {"size": 16, "color": THEME_DARK["font_color"], "family": "Inter, sans-serif"},
                "x": 0.05,
            },
            "paper_bgcolor": THEME_DARK["paper_bgcolor"],
            "plot_bgcolor": THEME_DARK["plot_bgcolor"],
            "font": {"color": THEME_DARK["font_color"], "family": "Inter, sans-serif"},
            "xaxis": {
                "title": {"text": x_label, "font": {"size": 12, "color": "#9ca3af"}},
                "gridcolor": THEME_DARK["grid_color"],
                "zerolinecolor": THEME_DARK["grid_color"],
                "showline": True,
                "linecolor": THEME_DARK["grid_color"],
            },
            "yaxis": {
                "title": {"text": y_label, "font": {"size": 12, "color": "#9ca3af"}},
                "gridcolor": THEME_DARK["grid_color"],
                "zerolinecolor": THEME_DARK["grid_color"],
                "showline": True,
                "linecolor": THEME_DARK["grid_color"],
            },
            "margin": {"l": 50, "r": 30, "t": 60, "b": 50},
            "hovermode": "closest",
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
                "font": {"color": THEME_DARK["font_color"]},
            },
        }

    @staticmethod
    def _base_config() -> dict[str, Any]:
        return {
            "responsive": True,
            "displayModeBar": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
            "toImageButtonOptions": {
                "format": "png",
                "filename": "chart_export",
                "height": 600,
                "width": 1000,
                "scale": 2,
            },
        }

    MAX_BROWSER_DATAPOINTS: int = 2500

    @staticmethod
    def _build_ag_grid(df: pd.DataFrame) -> dict[str, Any]:
        """Generate AG Grid column definitions, row data, and pagination schema."""
        if df.empty:
            return {
                "columnDefs": [],
                "rowData": [],
                "pagination": {"enabled": True, "pageSize": 50, "totalRows": 0, "displayedRows": 0},
            }

        col_defs = []
        for col in df.columns:
            is_num = pd.api.types.is_numeric_dtype(df[col])
            col_defs.append({
                "field": str(col),
                "headerName": str(col).replace("_", " ").title(),
                "sortable": True,
                "filter": "agNumberColumnFilter" if is_num else "agTextColumnFilter",
                "resizable": True,
            })

        # Replace NaN / Inf for JSON serialization
        clean_df = df.copy().replace({np.nan: None})
        row_data = clean_df.head(500).to_dict(orient="records")
        return {
            "columnDefs": col_defs,
            "rowData": row_data,
            "pagination": {
                "enabled": True,
                "pageSize": 50,
                "totalRows": int(len(df)),
                "displayedRows": int(min(len(df), 500)),
                "is_paginated": len(df) > 50,
            },
        }

    def _downsample_or_aggregate(
        self,
        df: pd.DataFrame,
        chart_name: str,
        x_col: str,
        y_col: str,
        max_points: int = 2500,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Protect browser memory and rendering responsiveness for large datasets (e.g. 500,000 rows).
        
        Applies aggregation (for categorical/bar/area/treemap) or stride sampling
        (for continuous/scatter/line) when rows exceed max_points.
        """
        orig_len = len(df)
        if orig_len <= max_points:
            return df, {
                "sampled": False,
                "strategy": "none",
                "original_rows": orig_len,
                "rendered_rows": orig_len,
                "max_browser_limit": max_points,
            }

        # Strategy 1: Aggregation for categorical/grouped charts
        categorical_types = {"bar", "bar_chart", "treemap", "funnel", "funnel_chart", "pareto", "pareto_chart"}
        if chart_name in categorical_types and x_col in df.columns and y_col in df.columns:
            try:
                if pd.api.types.is_numeric_dtype(df[y_col]):
                    agg_df = df.groupby(x_col, as_index=False)[y_col].sum()
                    if len(agg_df) > max_points:
                        agg_df = agg_df.sort_values(by=y_col, ascending=False)
                        top_df = agg_df.iloc[: max_points - 1]
                        other_val = agg_df.iloc[max_points - 1 :][y_col].sum()
                        other_row = pd.DataFrame([{x_col: "Other", y_col: other_val}])
                        agg_df = pd.concat([top_df, other_row], ignore_index=True)
                    return agg_df, {
                        "sampled": True,
                        "strategy": "group_aggregation",
                        "original_rows": orig_len,
                        "rendered_rows": len(agg_df),
                        "max_browser_limit": max_points,
                    }
            except Exception as e:
                logger.warning("Aggregation failed, falling back to stride sampling: %s", e)

        # Strategy 2: Stride downsampling for continuous/line/scatter charts
        step = int(np.ceil(orig_len / max_points))
        sampled_df = df.iloc[::step].copy()
        if orig_len > 1 and df.index[-1] not in sampled_df.index:
            sampled_df = pd.concat([sampled_df, df.iloc[[-1]]])

        return sampled_df, {
            "sampled": True,
            "strategy": "stride_sampling",
            "stride_step": step,
            "original_rows": orig_len,
            "rendered_rows": len(sampled_df),
            "max_browser_limit": max_points,
        }

    def generate_spec(
        self,
        chart_type: str,
        data: list[dict[str, Any]] | pd.DataFrame,
        x: str | None = None,
        y: str | None = None,
        title: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Convenience method accepting DataFrame or list of dict records returning full Plotly spec."""
        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        return self.generate_chart(chart_type=chart_type, df=df, x_col=x, y_col=y, title=title, **kwargs)

    def generate_chart(
        self,
        chart_type: str,
        df: pd.DataFrame,
        x_col: str | None = None,
        y_col: str | None = None,
        title: str = "",
        hierarchy: list[str] | None = None,
        color_by: str | None = None,
    ) -> dict[str, Any]:
        """Generate complete enterprise visualization payload with scalability protections."""
        if df.empty:
            return self._empty_chart(title or "No Data Available")

        cols = list(df.columns)
        x = x_col or (cols[0] if cols else "x")
        y = y_col or (cols[1] if len(cols) > 1 else cols[0])

        chart_name = chart_type.lower()

        # Apply browser scalability guardrail
        chart_df, scale_meta = self._downsample_or_aggregate(
            df=df, chart_name=chart_name, x_col=x, y_col=y, max_points=self.MAX_BROWSER_DATAPOINTS
        )

        if chart_name == "line_chart" or chart_name == "line":
            res = self.build_line_chart(chart_df, x, y, title=title or f"{y} over {x}")
        elif chart_name == "bar_chart" or chart_name == "bar":
            res = self.build_bar_chart(chart_df, x, y, title=title or f"{y} by {x}", color_by=color_by)
        elif chart_name == "area_chart" or chart_name == "area":
            res = self.build_area_chart(chart_df, x, y, title=title or f"{y} Trend Area")
        elif chart_name == "treemap":
            res = self.build_treemap(chart_df, hierarchy=hierarchy or [x], value_col=y, title=title or f"{y} Distribution Treemap")
        elif chart_name == "heatmap":
            res = self.build_heatmap(chart_df, title=title or "Correlation & Density Heatmap")
        elif chart_name == "scatter_plot" or chart_name == "scatter":
            res = self.build_scatter_plot(chart_df, x, y, title=title or f"{y} vs {x} Scatter Analysis", color_by=color_by)
        elif chart_name == "kpi_card" or chart_name == "kpi":
            res = self.build_kpi_card(chart_df, value_col=y, title=title or f"Key Metric: {y}")
        elif chart_name == "waterfall_chart" or chart_name == "waterfall":
            res = self.build_waterfall_chart(chart_df, x, y, title=title or f"Variance Breakdown: {y}")
        elif chart_name == "funnel_chart" or chart_name == "funnel":
            res = self.build_funnel_chart(chart_df, x, y, title=title or f"Funnel Progression: {y}")
        elif chart_name == "pareto_chart" or chart_name == "pareto":
            res = self.build_pareto_chart(chart_df, x, y, title=title or f"Pareto Analysis (80/20): {y}")
        else:
            res = self.build_bar_chart(chart_df, x, y, title=title or f"{y} by {x}")

        if "powerbi_meta" in res and isinstance(res["powerbi_meta"], dict):
            res["powerbi_meta"]["scalability"] = scale_meta
        return res


    def _empty_chart(self, title: str) -> dict[str, Any]:
        return {
            "chart_type": "empty",
            "data": [],
            "layout": self._base_layout(title),
            "config": self._base_config(),
            "powerbi_meta": {"drilldown": None, "cross_filtering": False, "export_options": ["png"]},
            "ag_grid_spec": {"columnDefs": [], "rowData": []},
        }

    # 1. Line Chart
    def build_line_chart(self, df: pd.DataFrame, x_col: str, y_col: str, title: str) -> dict[str, Any]:
        data = [{
            "type": "scatter",
            "mode": "lines+markers",
            "name": y_col,
            "x": df[x_col].astype(str).tolist(),
            "y": df[y_col].tolist(),
            "line": {"color": THEME_DARK["accent_primary"], "width": 3, "shape": "spline"},
            "marker": {"size": 6, "color": THEME_DARK["accent_secondary"]},
            "hovertemplate": f"<b>{x_col}</b>: %{{x}}<br><b>{y_col}</b>: %{{y:,.2f}}<extra></extra>",
        }]
        layout = self._base_layout(title, x_label=x_col, y_label=y_col)
        return {
            "chart_type": "line_chart",
            "data": data,
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "drilldown": {"dimension": x_col, "has_child_level": False},
                "cross_filtering": {"enabled": True, "dimension": x_col},
                "tooltips": {"format": "currency_or_number"},
                "export_options": ["png", "svg", "csv", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    # 2. Bar Chart
    def build_bar_chart(
        self, df: pd.DataFrame, x_col: str, y_col: str, title: str, color_by: str | None = None
    ) -> dict[str, Any]:
        data = [{
            "type": "bar",
            "name": y_col,
            "x": df[x_col].astype(str).tolist(),
            "y": df[y_col].tolist(),
            "marker": {
                "color": THEME_DARK["palette"][:len(df)] if len(df) <= len(THEME_DARK["palette"]) else THEME_DARK["accent_primary"],
                "opacity": 0.9,
                "line": {"width": 1, "color": THEME_DARK["grid_color"]},
            },
            "hovertemplate": f"<b>{x_col}</b>: %{{x}}<br><b>{y_col}</b>: %{{y:,.2f}}<extra></extra>",
        }]
        layout = self._base_layout(title, x_label=x_col, y_label=y_col)
        return {
            "chart_type": "bar_chart",
            "data": data,
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "drilldown": {"dimension": x_col, "has_child_level": True},
                "cross_filtering": {"enabled": True, "dimension": x_col},
                "tooltips": {"format": "number"},
                "export_options": ["png", "svg", "csv", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    # 3. Area Chart
    def build_area_chart(self, df: pd.DataFrame, x_col: str, y_col: str, title: str) -> dict[str, Any]:
        data = [{
            "type": "scatter",
            "mode": "lines",
            "name": y_col,
            "x": df[x_col].astype(str).tolist(),
            "y": df[y_col].tolist(),
            "fill": "tozeroy",
            "fillcolor": "rgba(59, 130, 246, 0.25)",
            "line": {"color": THEME_DARK["accent_primary"], "width": 2.5},
            "hovertemplate": f"<b>{x_col}</b>: %{{x}}<br><b>{y_col}</b>: %{{y:,.2f}}<extra></extra>",
        }]
        layout = self._base_layout(title, x_label=x_col, y_label=y_col)
        return {
            "chart_type": "area_chart",
            "data": data,
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "drilldown": {"dimension": x_col, "has_child_level": False},
                "cross_filtering": {"enabled": True, "dimension": x_col},
                "tooltips": {"format": "number"},
                "export_options": ["png", "svg", "csv", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    # 4. Treemap
    def build_treemap(
        self, df: pd.DataFrame, hierarchy: list[str], value_col: str, title: str
    ) -> dict[str, Any]:
        labels = []
        parents = []
        values = []

        if len(hierarchy) >= 2:
            grouped = df.groupby(hierarchy)[value_col].sum().reset_index()
            # Parents
            parent_col = hierarchy[0]
            child_col = hierarchy[1]
            parent_totals = df.groupby(parent_col)[value_col].sum()
            for p, val in parent_totals.items():
                labels.append(str(p))
                parents.append("")
                values.append(float(val))
            for _, row in grouped.iterrows():
                labels.append(f"{row[child_col]} ({row[parent_col]})")
                parents.append(str(row[parent_col]))
                values.append(float(row[value_col]))
        else:
            dim = hierarchy[0]
            grouped = df.groupby(dim)[value_col].sum().reset_index()
            for _, row in grouped.iterrows():
                labels.append(str(row[dim]))
                parents.append("")
                values.append(float(row[value_col]))

        data = [{
            "type": "treemap",
            "labels": labels,
            "parents": parents,
            "values": values,
            "textinfo": "label+value+percent parent",
            "marker": {"colorscale": "Blues", "line": {"width": 1, "color": THEME_DARK["paper_bgcolor"]}},
            "hovertemplate": "<b>%{label}</b><br>Value: %{value:,.2f}<br>Share: %{percentRoot:.1%}<extra></extra>",
        }]
        layout = self._base_layout(title)
        return {
            "chart_type": "treemap",
            "data": data,
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "drilldown": {"hierarchy": hierarchy, "levels": len(hierarchy)},
                "cross_filtering": {"enabled": True, "dimension": hierarchy[0]},
                "export_options": ["png", "svg", "csv", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    # Donut Chart
    def build_donut_chart(
        self, df: pd.DataFrame, labels_col: str, values_col: str, title: str
    ) -> dict[str, Any]:
        data = [{
            "type": "pie",
            "hole": 0.55,
            "labels": df[labels_col].astype(str).tolist(),
            "values": df[values_col].tolist(),
            "marker": {
                "colors": THEME_DARK["palette"][:len(df)] if len(df) <= len(THEME_DARK["palette"]) else THEME_DARK["palette"],
                "line": {"color": THEME_DARK["paper_bgcolor"], "width": 2},
            },
            "textinfo": "label+percent",
            "hoverinfo": "label+value+percent",
        }]
        layout = self._base_layout(title)
        return {
            "chart_type": "donut_chart",
            "data": data,
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "cross_filtering": {"enabled": True, "dimension": labels_col},
                "tooltips": {"format": "percent_and_value"},
                "export_options": ["png", "svg", "csv", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    # 5. Heatmap
    def build_heatmap(self, df: pd.DataFrame, title: str) -> dict[str, Any]:
        num_df = df.select_dtypes(include=[np.number])
        if num_df.shape[1] >= 2:
            corr = num_df.corr().round(2)
            z = corr.values.tolist()
            x = corr.columns.tolist()
            y = corr.index.tolist()
        else:
            z = [[1.0, 0.5], [0.5, 1.0]]
            x = ["Var A", "Var B"]
            y = ["Var A", "Var B"]

        data = [{
            "type": "heatmap",
            "z": z,
            "x": x,
            "y": y,
            "colorscale": "Viridis",
            "hovertemplate": "<b>X</b>: %{x}<br><b>Y</b>: %{y}<br><b>Value</b>: %{z:.2f}<extra></extra>",
        }]
        layout = self._base_layout(title)
        return {
            "chart_type": "heatmap",
            "data": data,
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "drilldown": None,
                "cross_filtering": {"enabled": True, "dimension": "matrix_cell"},
                "export_options": ["png", "svg", "csv", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    # 6. Scatter Plot
    def build_scatter_plot(
        self, df: pd.DataFrame, x_col: str, y_col: str, title: str, color_by: str | None = None
    ) -> dict[str, Any]:
        data = [{
            "type": "scatter",
            "mode": "markers",
            "name": f"{y_col} vs {x_col}",
            "x": df[x_col].tolist(),
            "y": df[y_col].tolist(),
            "marker": {
                "size": 8,
                "color": THEME_DARK["accent_primary"],
                "opacity": 0.8,
                "line": {"width": 1, "color": THEME_DARK["font_color"]},
            },
            "hovertemplate": f"<b>{x_col}</b>: %{{x}}<br><b>{y_col}</b>: %{{y:,.2f}}<extra></extra>",
        }]
        layout = self._base_layout(title, x_label=x_col, y_label=y_col)
        return {
            "chart_type": "scatter_plot",
            "data": data,
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "drilldown": None,
                "cross_filtering": {"enabled": True, "dimension": x_col},
                "export_options": ["png", "svg", "csv", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    # 7. KPI Card
    def build_kpi_card(self, df: pd.DataFrame, value_col: str, title: str) -> dict[str, Any]:
        val = 0.0
        if value_col in df.columns and pd.api.types.is_numeric_dtype(df[value_col]):
            val = float(df[value_col].sum() if len(df) > 1 else df[value_col].iloc[0])
        elif not df.empty and pd.api.types.is_numeric_dtype(df.iloc[:, 0]):
            val = float(df.iloc[:, 0].sum())

        data = [{
            "type": "indicator",
            "mode": "number+delta",
            "value": val,
            "title": {"text": title, "font": {"size": 18, "color": THEME_DARK["font_color"]}},
            "number": {"font": {"size": 48, "color": THEME_DARK["accent_secondary"]}},
        }]
        layout = {
            "paper_bgcolor": THEME_DARK["paper_bgcolor"],
            "plot_bgcolor": THEME_DARK["plot_bgcolor"],
            "font": {"color": THEME_DARK["font_color"], "family": "Inter, sans-serif"},
            "margin": {"l": 20, "r": 20, "t": 40, "b": 20},
        }
        return {
            "chart_type": "kpi_card",
            "data": data,
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "kpi_value": val,
                "metric_name": value_col,
                "export_options": ["png", "svg", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    # 8. Waterfall Chart
    def build_waterfall_chart(self, df: pd.DataFrame, x_col: str, y_col: str, title: str) -> dict[str, Any]:
        x_vals = df[x_col].astype(str).tolist()
        y_vals = [float(v) for v in df[y_col].tolist()]
        measures = ["relative"] * len(y_vals)
        if len(measures) > 2:
            measures[-1] = "total"

        data = [{
            "type": "waterfall",
            "name": y_col,
            "orientation": "v",
            "measure": measures,
            "x": x_vals,
            "y": y_vals,
            "connector": {"line": {"color": THEME_DARK["grid_color"]}},
            "decreasing": {"marker": {"color": THEME_DARK["accent_danger"]}},
            "increasing": {"marker": {"color": THEME_DARK["accent_secondary"]}},
            "totals": {"marker": {"color": THEME_DARK["accent_primary"]}},
            "hovertemplate": "<b>%{x}</b><br>Delta: %{y:,.2f}<extra></extra>",
        }]
        layout = self._base_layout(title, x_label=x_col, y_label=y_col)
        return {
            "chart_type": "waterfall_chart",
            "data": data,
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "drilldown": None,
                "cross_filtering": {"enabled": True, "dimension": x_col},
                "export_options": ["png", "svg", "csv", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    # 9. Funnel Chart
    def build_funnel_chart(self, df: pd.DataFrame, x_col: str, y_col: str, title: str) -> dict[str, Any]:
        sorted_df = df.sort_values(by=y_col, ascending=False)
        data = [{
            "type": "funnel",
            "y": sorted_df[x_col].astype(str).tolist(),
            "x": sorted_df[y_col].tolist(),
            "textinfo": "value+percent initial",
            "marker": {"color": THEME_DARK["palette"][:len(sorted_df)]},
            "hovertemplate": "<b>%{y}</b><br>Volume: %{x:,.0f}<br>Retention: %{percentInitial:.1%}<extra></extra>",
        }]
        layout = self._base_layout(title, x_label=y_col, y_label=x_col)
        return {
            "chart_type": "funnel_chart",
            "data": data,
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "stages": sorted_df[x_col].tolist(),
                "cross_filtering": {"enabled": True, "dimension": x_col},
                "export_options": ["png", "svg", "csv", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    # 10. Pareto Chart
    def build_pareto_chart(self, df: pd.DataFrame, x_col: str, y_col: str, title: str) -> dict[str, Any]:
        sorted_df = df.sort_values(by=y_col, ascending=False).copy()
        total_sum = sorted_df[y_col].sum()
        cum_pct = (sorted_df[y_col].cumsum() / total_sum * 100.0) if total_sum > 0 else 0

        bar_trace = {
            "type": "bar",
            "name": y_col,
            "x": sorted_df[x_col].astype(str).tolist(),
            "y": sorted_df[y_col].tolist(),
            "marker": {"color": THEME_DARK["accent_primary"], "opacity": 0.85},
            "hovertemplate": f"<b>{x_col}</b>: %{{x}}<br><b>{y_col}</b>: %{{y:,.2f}}<extra></extra>",
        }
        line_trace = {
            "type": "scatter",
            "mode": "lines+markers",
            "name": "Cumulative %",
            "x": sorted_df[x_col].astype(str).tolist(),
            "y": cum_pct.tolist() if isinstance(cum_pct, pd.Series) else [0] * len(sorted_df),
            "yaxis": "y2",
            "line": {"color": THEME_DARK["accent_warning"], "width": 3},
            "marker": {"size": 6, "color": THEME_DARK["accent_warning"]},
            "hovertemplate": "<b>Cumulative %</b>: %{y:.1f}%<extra></extra>",
        }

        layout = self._base_layout(title, x_label=x_col, y_label=y_col)
        layout["yaxis2"] = {
            "title": {"text": "Cumulative %", "font": {"size": 12, "color": THEME_DARK["accent_warning"]}},
            "overlaying": "y",
            "side": "right",
            "range": [0, 105],
            "showgrid": False,
        }

        return {
            "chart_type": "pareto_chart",
            "data": [bar_trace, line_trace],
            "layout": layout,
            "config": self._base_config(),
            "powerbi_meta": {
                "pareto_threshold_80": True,
                "cross_filtering": {"enabled": True, "dimension": x_col},
                "export_options": ["png", "svg", "csv", "json"],
            },
            "ag_grid_spec": self._build_ag_grid(df),
        }

    def create_line_chart(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        df = kwargs.get("df", kwargs.get("data", args[0] if len(args) > 0 else None))
        x = kwargs.get("x_col", kwargs.get("x", args[1] if len(args) > 1 else None))
        y = kwargs.get("y_col", kwargs.get("y", args[2] if len(args) > 2 else None))
        title = kwargs.get("title", args[3] if len(args) > 3 else "")
        return self.build_line_chart(df, str(x), str(y), str(title))

    def create_bar_chart(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        df = kwargs.get("df", kwargs.get("data", args[0] if len(args) > 0 else None))
        x = kwargs.get("x_col", kwargs.get("x", args[1] if len(args) > 1 else None))
        y = kwargs.get("y_col", kwargs.get("y", args[2] if len(args) > 2 else None))
        title = kwargs.get("title", args[3] if len(args) > 3 else "")
        return self.build_bar_chart(df, str(x), str(y), str(title))

    def create_donut_chart(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        df = kwargs.get("df", kwargs.get("data", args[0] if len(args) > 0 else None))
        labels = kwargs.get("labels_col", kwargs.get("labels", kwargs.get("x", args[1] if len(args) > 1 else None)))
        values = kwargs.get("values_col", kwargs.get("values", kwargs.get("y", args[2] if len(args) > 2 else None)))
        title = kwargs.get("title", args[3] if len(args) > 3 else "")
        return self.build_donut_chart(df, str(labels), str(values), str(title))

    def create_area_chart(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        df = kwargs.get("df", kwargs.get("data", args[0] if len(args) > 0 else None))
        x = kwargs.get("x_col", kwargs.get("x", args[1] if len(args) > 1 else None))
        y = kwargs.get("y_col", kwargs.get("y", args[2] if len(args) > 2 else None))
        title = kwargs.get("title", args[3] if len(args) > 3 else "")
        return self.build_area_chart(df, str(x), str(y), str(title))



__all__ = ["PlotlyEngine", "THEME_DARK"]

