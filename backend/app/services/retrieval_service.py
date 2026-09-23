"""Alias for DataRetrievalService to maintain naming consistency."""

from backend.app.services.data_retrieval_service import (
    DataRetrievalService as RetrievalService,
    get_data_retrieval_service as get_retrieval_service,
)

__all__ = ["RetrievalService", "get_retrieval_service"]
