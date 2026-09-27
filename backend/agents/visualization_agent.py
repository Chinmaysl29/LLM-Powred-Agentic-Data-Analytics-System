"""Enterprise Visualization Agent.

Generates Power BI-grade interactive charts (Plotly figure JSON + AG Grid schema)
based on prior analytical or SQL outputs in the workflow context.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.agent_registry import BaseAgentRunner
from backend.app.services.data_retrieval_service import DataRetrievalService
from backend.visualization.chart_selector import ChartSelector
from backend.visualization.generators.plotly_engine import PlotlyEngine

logger = logging.getLogger(__name__)


class VisualizationAgentRunner(BaseAgentRunner):
    """Concrete runner producing Power BI-level Plotly specifications for the Orchestrator pipeline."""

    def __init__(
        self,
        retrieval_service: DataRetrievalService | None = None,
        selector: ChartSelector | None = None,
        engine: PlotlyEngine | None = None,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._selector = selector or ChartSelector()
        self._engine = engine or PlotlyEngine()

    @property
    def name(self) -> str:
        return "visualization"

    async def run(self, context: WorkflowContext) -> dict[str, Any]:
        """Generate interactive Plotly dashboard spec based on workflow context data."""
        query = context.query
        df: pd.DataFrame | None = None

        # 1. First priority: Use SQL agent output if available
        sql_result = context.results.get("sql", {})
        if isinstance(sql_result, dict) and sql_result.get("rows"):
            df = pd.DataFrame(sql_result["rows"])

        # 2. Second priority: Use DataRetrievalService for active dataset
        if df is None or df.empty:
            dataset_id = context.dataset_id
            if dataset_id and self._retrieval_service:
                try:
                    df, _ = self._retrieval_service.load_dataframe(dataset_id=dataset_id)
                except Exception as e:
                    logger.warning("VisualizationAgentRunner failed loading dataset DataFrame: %s", e)

        # 3. Third priority: Check for records in metadata or other agent results
        if df is None or df.empty:
            if "retrieved_data" in context.results and context.results["retrieved_data"].get("records"):
                df = pd.DataFrame(context.results["retrieved_data"]["records"])
            elif "records" in context.metadata:
                df = pd.DataFrame(context.metadata["records"])

        # If still no data, generate an informational empty chart
        if df is None or df.empty:
            empty_spec = self._engine.generate_chart(
                chart_type="bar_chart",
                df=pd.DataFrame(),
                title=f"Visualization for '{query}' (No Data Available)",
            )
            return {
                "chart_spec": empty_spec,
                "recommended_chart": "bar_chart",
                "status": "no_data",
                "summary": f"Could not generate visual charts for '{query}' because no underlying dataset rows were found.",
            }

        # 4. Recommend optimal chart type
        recommendation = self._selector.select(df, query=query)
        logger.info(
            "VisualizationAgent selected %s (confidence=%.2f) for query='%s'",
            recommendation.chart_type,
            recommendation.confidence,
            query,
        )

        # 5. Generate Power BI-grade Plotly Specification
        chart_spec = self._engine.generate_chart(
            chart_type=recommendation.chart_type,
            df=df,
            x_col=recommendation.x_axis,
            y_col=recommendation.y_axis,
            title=f"Analysis: {query.title() if len(query) < 40 else query[:40] + '...'}",
            hierarchy=recommendation.hierarchy,
            color_by=recommendation.color_by,
        )

        return {
            "chart_type": recommendation.chart_type,
            "confidence": recommendation.confidence,
            "selection_reason": recommendation.reason,
            "chart_spec": chart_spec,
            "powerbi_features": {
                "interactive_tooltips": True,
                "drilldown_enabled": bool(chart_spec.get("powerbi_meta", {}).get("drilldown")),
                "cross_filtering_enabled": chart_spec.get("powerbi_meta", {}).get("cross_filtering", {}).get("enabled", False),
                "export_formats": ["PNG", "SVG", "CSV", "JSON"],
                "ag_grid_companion": True,
            },
            "status": "success",
            "summary": (
                f"Generated interactive {recommendation.chart_type.replace('_', ' ').title()} "
                f"with Power BI drilldown and dark slate theme for: '{query}'."
            ),
        }


__all__ = ["VisualizationAgentRunner"]
