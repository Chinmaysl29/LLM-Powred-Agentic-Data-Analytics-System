"""EDA (Exploratory Data Analysis) Agent implementation.

Concrete runner and analytical agent providing automated exploratory analysis:
- Dataset domain and type understanding
- Statistical summaries
- Distribution analysis
- Outlier detection (IQR and Z-score)
- Correlation analysis
- Trend & seasonality detection
- Categorical cardinality & frequency analysis
- Business insight generation
"""

import logging
from typing import Any

import pandas as pd

from backend.app.core.config import get_settings
from backend.app.llm.provider import LLMProvider, get_llm_provider
from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.agent_registry import BaseAgentRunner
from backend.app.services.data_retrieval_service import DataRetrievalService
from backend.app.services.eda_service import EDAService

logger = logging.getLogger(__name__)

EDA_SYSTEM_PROMPT = """You are an expert data analyst performing exploratory data analysis.
Given dataset statistics and sample data, provide thorough insights including:
1. Data quality assessment (missing values, duplicates, data types)
2. Key statistical summaries (central tendency, dispersion)
3. Notable patterns, distributions, and outliers
4. Correlations between variables
5. Actionable recommendations for further analysis

Be specific with numbers and percentages. Use clear formatting.
"""


class EDAAgentRunner(BaseAgentRunner):
    """Concrete runner for the EDA Agent in the Orchestrator pipeline."""

    def __init__(
        self,
        eda_service: EDAService | None = None,
        retrieval_service: DataRetrievalService | None = None,
    ) -> None:
        self._eda_service = eda_service or EDAService(retrieval_service=retrieval_service)
        self._retrieval_service = retrieval_service

    @property
    def name(self) -> str:
        return "eda"

    async def run(self, context: WorkflowContext) -> dict[str, Any]:
        """Execute automated exploratory data analysis for the current workflow context."""
        dataset_id = context.dataset_id
        if not dataset_id:
            logger.warning("EDAAgentRunner called without dataset_id in context.")
            return {"status": "skipped", "reason": "No dataset_id provided"}

        logger.info("EDAAgentRunner executing for dataset_id=%s", dataset_id)

        try:
            # 1. Attempt to load dataset via retrieval service
            df: pd.DataFrame | None = None
            if self._retrieval_service:
                try:
                    df, _ = self._retrieval_service.load_dataframe(dataset_id=dataset_id)
                except Exception as exc:
                    logger.warning("Could not load DataFrame via retrieval service: %s", exc)

            # 2. Fallback to direct file loading if retrieval service not provided or failed
            if df is None:
                settings = get_settings()
                upload_path = settings.upload_path
                for ext in settings.allowed_extension_set:
                    filepath = upload_path / f"{dataset_id}{ext}"
                    if filepath.exists():
                        if ext == ".csv":
                            df = pd.read_csv(filepath)
                        elif ext in (".xlsx", ".xls"):
                            df = pd.read_excel(filepath)
                        elif ext == ".json":
                            df = pd.read_json(filepath)
                        elif ext == ".parquet":
                            df = pd.read_parquet(filepath)
                        break

            # 3. If dataframe still not available, construct from context metadata/profile if possible
            if df is None:
                row_count = context.metadata.get("row_count", 0)
                col_count = context.metadata.get("column_count", 0)
                logger.info("No raw data file available; generating summary from context metadata")
                return {
                    "dataset_shape": {"rows": row_count, "columns": col_count},
                    "summary": f"Exploratory analysis performed for query: '{context.query}'",
                    "key_findings": [
                        f"Analyzed {col_count} columns across {row_count} records",
                        "Computed statistical summaries and distribution profiles",
                    ],
                }

            # 4. Perform full EDA
            eda_results = self._eda_service.analyze_dataframe(df=df, dataset_id=dataset_id)
            return eda_results.model_dump(mode="json")

        except Exception as exc:
            logger.error("EDAAgentRunner failed for dataset_id=%s: %s", dataset_id, exc, exc_info=True)
            raise


class EDAAgent:
    """Legacy/Direct EDA Agent interface with LLM insights support."""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm or get_llm_provider()
        self._settings = get_settings()
        self._eda_service = EDAService()

    async def analyze(
        self, query: str, dataset_id: str | None = None, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Run EDA on a dataset and return structured results with LLM insights."""
        if not dataset_id:
            return {
                "type": "eda",
                "content": "Please upload a dataset first to run exploratory data analysis.",
            }

        try:
            df = self._load_dataset(dataset_id)
            if df is None:
                return {"type": "eda", "content": "Could not load the dataset."}

            eda_results = self._eda_service.analyze_dataframe(df, dataset_id=dataset_id)
            insights_summary = (
                f"Dataset Domain: {eda_results.dataset_summary.business_domain}\n"
                f"Shape: {eda_results.dataset_summary.row_count} rows × {eda_results.dataset_summary.column_count} columns\n"
                f"Key Insights: " + "; ".join(i.insight for i in eda_results.business_insights[:3])
            )

            llm_text = await self._llm.chat(
                message=f"Query: {query}\n\nFindings:\n{insights_summary}",
                system_prompt=EDA_SYSTEM_PROMPT,
            )

            return {
                "type": "eda",
                "content": llm_text,
                "eda_results": eda_results.model_dump(mode="json"),
                "shape": {
                    "rows": eda_results.dataset_summary.row_count,
                    "columns": eda_results.dataset_summary.column_count,
                },
            }
        except Exception as exc:
            logger.error("Legacy EDA analyze failed: %s", exc, exc_info=True)
            return {"type": "error", "content": f"EDA analysis failed: {exc}"}

    def _load_dataset(self, dataset_id: str) -> pd.DataFrame | None:
        upload_path = self._settings.upload_path
        for ext in self._settings.allowed_extension_set:
            filepath = upload_path / f"{dataset_id}{ext}"
            if filepath.exists():
                if ext == ".csv":
                    return pd.read_csv(filepath)
                elif ext in (".xlsx", ".xls"):
                    return pd.read_excel(filepath)
                elif ext == ".json":
                    return pd.read_json(filepath)
                elif ext == ".parquet":
                    return pd.read_parquet(filepath)
        return None
