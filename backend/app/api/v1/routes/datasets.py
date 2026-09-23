"""Dataset API routes for Phase 2.1 Dataset Foundation."""

import logging
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status, Query

from backend.app.models.dataset import Dataset
from backend.app.models.dataset_metadata import DatasetMetadata
from backend.app.models.dataset_profile import DatasetProfile
from backend.app.models.dataset_quality import DatasetQuality
from backend.app.repositories.dataset_repository import (
    DatasetRepository,
    get_dataset_repository,
)
from backend.app.repositories.dataset_metadata_repository import (
    DatasetMetadataRepository,
    get_dataset_metadata_repository,
)
from backend.app.repositories.dataset_profile_repository import (
    DatasetProfileRepository,
    get_dataset_profile_repository,
)
from backend.app.repositories.dataset_quality_repository import (
    DatasetQualityRepository,
    get_dataset_quality_repository,
)
from backend.app.repositories.dataset_recommendation_repository import (
    DatasetRecommendationRepository,
    get_dataset_recommendation_repository,
)
from backend.app.schemas.dataset import (
    DatasetListResponse,
    DatasetResponse,
    DatasetUpdate,
    DatasetUploadResponse,
)
from backend.app.schemas.dataset_metadata import DatasetMetadataResponse
from backend.app.schemas.dataset_profile import DatasetProfileResponse
from backend.app.schemas.dataset_quality import DatasetQualityResponse
from backend.app.services.storage_service import StorageService, get_storage_service
from backend.app.services.metadata_extraction_service import (
    MetadataExtractionService,
    get_metadata_extraction_service,
)
from backend.app.services.data_profiling_service import (
    DataProfilingService,
    get_data_profiling_service,
)
from backend.app.services.data_quality_service import (
    DataQualityService,
    get_data_quality_service,
)
from backend.app.services.dataset_versioning_service import (
    DatasetVersioningService,
    get_dataset_versioning_service,
    VersioningError,
)
from backend.app.schemas.dataset_version import (
    DatasetVersionResponse,
    DatasetVersionComparisonResponse,
    DatasetVersionListResponse,
)
from backend.app.services.data_cleaning_recommendation_service import (
    DataCleaningRecommendationService,
    get_data_cleaning_recommendation_service,
)
from backend.app.services.dataset_upload_service import (
    DatasetUploadService,
    get_dataset_upload_service,
)
from backend.app.schemas.dataset_recommendation import (
    DatasetRecommendationListResponse,
    DatasetRecommendationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new dataset file",
    description="Upload a CSV, XLSX, or JSON file, store it, create a dataset record, and return the dataset entity.",
)
async def upload_dataset(
    file: Annotated[UploadFile, File(description="CSV, XLSX, or JSON dataset file")],
    dataset_name: Annotated[str | None, Form(description="Optional custom dataset name")] = None,
    upload_service: DatasetUploadService = Depends(get_dataset_upload_service),
) -> Any:
    """Execute upload flow via dedicated DatasetUploadService."""
    logger.info("Received dataset upload request filename=%s", file.filename)
    return await upload_service.process_upload(file=file, dataset_name=dataset_name)


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Get dataset metadata by ID",
)
async def get_dataset(
    dataset_id: str,
    dataset_repository: DatasetRepository = Depends(get_dataset_repository),
) -> DatasetResponse:
    """Retrieve metadata for a specific dataset."""
    dataset = dataset_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found",
        )
    return DatasetResponse.model_validate(dataset)
@router.get(
    "/{dataset_id}/metadata",
    response_model=DatasetMetadataResponse,
    summary="Get dataset metadata by ID",
)
async def get_dataset_metadata(
    dataset_id: str,
    metadata_repository: DatasetMetadataRepository = Depends(get_dataset_metadata_repository),
) -> DatasetMetadataResponse:
    """Retrieve extracted metadata for a specific dataset."""
    metadata = metadata_repository.get(dataset_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metadata for dataset with ID '{dataset_id}' not found",
        )
    
    # We must convert the dictionary classifications to a structured response, since our model returns dict
    # but Pydantic expects DatasetClassification schema.
    # The dictionary matches exactly the DatasetClassification schema fields.
    return DatasetMetadataResponse.model_validate(metadata)


@router.get(
    "/{dataset_id}/profile",
    response_model=DatasetProfileResponse,
    summary="Get dataset profile by ID",
)
async def get_dataset_profile(
    dataset_id: str,
    profile_repository: DatasetProfileRepository = Depends(get_dataset_profile_repository),
) -> DatasetProfileResponse:
    """Retrieve statistical profile for a specific dataset."""
    profile = profile_repository.get(dataset_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile for dataset with ID '{dataset_id}' not found",
        )
    return DatasetProfileResponse.model_validate(profile)


@router.get(
    "/{dataset_id}/quality",
    response_model=DatasetQualityResponse,
    summary="Get dataset quality by ID",
)
async def get_dataset_quality(
    dataset_id: str,
    quality_repository: DatasetQualityRepository = Depends(get_dataset_quality_repository),
) -> DatasetQualityResponse:
    """Retrieve quality assessment for a specific dataset."""
    quality = quality_repository.get(dataset_id)
    if not quality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quality record for dataset with ID '{dataset_id}' not found",
        )
    return DatasetQualityResponse.model_validate(quality)


@router.get(
    "/{dataset_id}/versions",
    response_model=DatasetVersionListResponse,
    summary="List dataset versions",
)
async def list_dataset_versions(
    dataset_id: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    versioning_service: DatasetVersioningService = Depends(get_dataset_versioning_service),
    dataset_repository: DatasetRepository = Depends(get_dataset_repository),
) -> dict:
    """Retrieve all versions of a dataset."""
    if not dataset_repository.get(dataset_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found",
        )
    versions, total = versioning_service.dataset_version_repository.get_versions(dataset_id, limit, offset)
    active = versioning_service.dataset_version_repository.get_active_version(dataset_id)
    return {
        "versions": [DatasetVersionResponse.model_validate(v) for v in versions],
        "total_count": total,
        "current_active_version": active.version_number if active else None
    }


@router.get(
    "/{dataset_id}/versions/compare",
    response_model=DatasetVersionComparisonResponse,
    summary="Compare two dataset versions",
)
async def compare_dataset_versions(
    dataset_id: str,
    v1: Annotated[int, Query(description="First version number")],
    v2: Annotated[int, Query(description="Second version number")],
    versioning_service: DatasetVersioningService = Depends(get_dataset_versioning_service),
) -> DatasetVersionComparisonResponse:
    """Compare rows and columns between two versions."""
    try:
        return versioning_service.compare_versions(dataset_id, v1, v2)
    except VersioningError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{dataset_id}/versions/{version_number}",
    response_model=DatasetVersionResponse,
    summary="Get a specific dataset version",
)
async def get_dataset_version(
    dataset_id: str,
    version_number: int,
    versioning_service: DatasetVersioningService = Depends(get_dataset_versioning_service),
) -> DatasetVersionResponse:
    """Retrieve details for a specific version."""
    try:
        v = versioning_service.dataset_version_repository.get_version(dataset_id, version_number)
        return DatasetVersionResponse.model_validate(v)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/{dataset_id}/versions/{version_number}/rollback",
    summary="Rollback dataset to a specific version",
)
async def rollback_dataset_version(
    dataset_id: str,
    version_number: int,
    versioning_service: DatasetVersioningService = Depends(get_dataset_versioning_service),
) -> dict:
    """Set the specified version as active."""
    try:
        active = versioning_service.rollback_version(dataset_id, version_number)
        return {
            "message": "Rollback successful",
            "dataset_id": dataset_id,
            "rolled_back_to_version": active.version_number,
            "version_details": DatasetVersionResponse.model_validate(active).model_dump()
        }
    except VersioningError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/{dataset_id}/versions/{version_number}/lineage",
    summary="Get version lineage chain",
)
async def get_dataset_version_lineage(
    dataset_id: str,
    version_number: int,
    versioning_service: DatasetVersioningService = Depends(get_dataset_versioning_service),
) -> dict:
    """Retrieve the ancestry chain of a version."""
    try:
        chain = versioning_service.get_version_lineage(dataset_id, version_number)
        return {
            "dataset_id": dataset_id,
            "version_number": version_number,
            "lineage_chain": [c.model_dump() for c in chain]
        }
    except VersioningError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/{dataset_id}/recommendations",
    response_model=DatasetRecommendationListResponse,
    summary="List data cleaning recommendations",
)
async def list_dataset_recommendations(
    dataset_id: str,
    recommendation_repository: DatasetRecommendationRepository = Depends(get_dataset_recommendation_repository),
) -> DatasetRecommendationListResponse:
    """Retrieve active cleaning recommendations for the dataset."""
    recs = recommendation_repository.get_active_recommendations_for_dataset(dataset_id)

    total = len(recs)
    critical = sum(1 for r in recs if r.severity == 'critical')
    return DatasetRecommendationListResponse(
        dataset_id=dataset_id,
        version_id=recs[0].version_id if recs else "",
        total_count=total,
        active_count=total,
        critical_count=critical,
        recommendations=[DatasetRecommendationResponse.model_validate(r) for r in recs],
        estimated_quality_after_all_fixes=sum(r.estimated_quality_gain for r in recs),
        summary=f"{critical} critical, {total - critical} other recommendations",
    )


@router.post(
    "/{dataset_id}/recommendations/{recommendation_id}/resolve",
    response_model=DatasetRecommendationResponse,
    summary="Mark recommendation as resolved",
)
async def resolve_dataset_recommendation(
    dataset_id: str,
    recommendation_id: str,
    recommendation_repository: DatasetRecommendationRepository = Depends(get_dataset_recommendation_repository),
) -> DatasetRecommendationResponse:
    """Mark a recommendation as resolved after acting on it."""
    try:
        rec = recommendation_repository.mark_resolved(recommendation_id)
        return DatasetRecommendationResponse.model_validate(rec)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get(
    "",
    response_model=list[DatasetResponse],
    summary="List all datasets",
)
async def list_datasets(
    skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Max records to return")] = 50,
    dataset_repository: DatasetRepository = Depends(get_dataset_repository),
) -> list[DatasetResponse]:
    """List datasets ordered by creation time descending."""
    datasets = dataset_repository.list(skip=skip, limit=limit)
    return [DatasetResponse.model_validate(d) for d in datasets]


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a dataset",
)
async def delete_dataset(
    dataset_id: str,
    dataset_repository: DatasetRepository = Depends(get_dataset_repository),
    storage_service: StorageService = Depends(get_storage_service),
) -> dict[str, str | bool]:
    """Delete dataset record and its backing storage file."""
    dataset = dataset_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found",
        )

    # Delete the isolated source plus canonical artifacts.
    if not storage_service.delete_dataset(dataset_id):
        # Datasets uploaded before Phase 17.11 used a flat source-file layout.
        storage_service.delete_file(dataset.file_path)

    # Delete database record
    dataset_repository.delete(dataset_id)
    logger.info("Dataset deleted successfully dataset_id=%s", dataset_id)

    return {"success": True, "message": f"Dataset '{dataset_id}' deleted successfully"}
