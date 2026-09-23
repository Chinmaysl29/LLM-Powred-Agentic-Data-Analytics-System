"""Data Retrieval Agent implementation."""

import logging
from typing import Any

from backend.app.schemas.orchestrator import WorkflowContext
from backend.app.services.agent_registry import BaseAgentRunner
from backend.app.services.data_retrieval_service import DataRetrievalService

logger = logging.getLogger(__name__)


class DataRetrievalAgentRunner(BaseAgentRunner):
    """Concrete runner for the Data Retrieval Agent.
    
    Acts as the single source of truth for downstream agents by loading, filtering,
    sampling, and packaging dataset context.
    """

    def __init__(self, retrieval_service: DataRetrievalService):
        self._retrieval_service = retrieval_service

    @property
    def name(self) -> str:
        return "data_retrieval"

    async def run(self, context: WorkflowContext) -> dict[str, Any]:
        """Execute the data retrieval task and return packaged context."""
        dataset_id = context.dataset_id
        if not dataset_id:
            logger.warning("DataRetrievalAgentRunner called without dataset_id in context.")
            return {"status": "skipped", "reason": "No dataset_id provided"}

        logger.info("DataRetrievalAgentRunner executing for dataset_id=%s", dataset_id)

        try:
            # For phase 3.4, we just retrieve the active version without filters (filters can be extracted from query later)
            # The schema states we return the dictionary representation of PackagedDatasetContext
            packaged_context = self._retrieval_service.get_packaged_context(dataset_id=dataset_id)
            
            # The packaged context can be dumped to a dict
            return packaged_context.model_dump(mode="json", exclude_none=True)
            
        except Exception as e:
            logger.error("DataRetrievalAgentRunner failed: %s", e)
            raise
