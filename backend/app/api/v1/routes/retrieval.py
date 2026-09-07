"""API routes for Data Retrieval Agent."""

import logging
from typing import Any

from fastapi import APIRouter, Depends

from backend.app.schemas.retrieval import (
    DataRetrievalFilter,
    DataRetrievalRequest,
    DatasetSchemaResponse,
    PackagedDatasetContext,
)
from backend.app.services.data_retrieval_service import (
    DataRetrievalService,
    get_data_retrieval_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])


@router.get(
    "/{dataset_id}/package",
    response_model=PackagedDatasetContext,
    summary="Get packaged dataset context",
)
async def get_dataset_package(
    dataset_id: str,
    version: int | None = None,
    service: DataRetrievalService = Depends(get_data_retrieval_service),
) -> PackagedDatasetContext:
    """Retrieve the standard packaged dataset context for a given dataset."""
    return service.get_packaged_context(dataset_id=dataset_id, version_number=version)


@router.get(
    "/{dataset_id}/schema",
    response_model=DatasetSchemaResponse,
    summary="Get dataset schema",
)
async def get_dataset_schema(
    dataset_id: str,
    version: int | None = None,
    service: DataRetrievalService = Depends(get_data_retrieval_service),
) -> DatasetSchemaResponse:
    """Perform a fast schema lookup without full data load."""
    return service.get_schema(dataset_id=dataset_id, version_number=version)


@router.post(
    "/{dataset_id}/query",
    summary="Query dataset with filters and sampling",
)
async def query_dataset(
    dataset_id: str,
    request: DataRetrievalRequest,
    service: DataRetrievalService = Depends(get_data_retrieval_service),
) -> dict[str, Any]:
    """Retrieve actual data rows with optional filters and sampling applied."""
    df, is_sampled = service.load_dataframe(
        dataset_id=dataset_id,
        version_number=request.version_number,
        filters=request.filters,
        sample_size=request.sample_size,
    )
    
    # We could also paginate here using request.limit, but for now we just return top N
    if request.limit and len(df) > request.limit:
        df = df.head(request.limit)

    records = df.to_dict(orient="records")
    return {
        "dataset_id": dataset_id,
        "is_sampled": is_sampled,
        "total_rows_returned": len(records),
        "data": records
    }
