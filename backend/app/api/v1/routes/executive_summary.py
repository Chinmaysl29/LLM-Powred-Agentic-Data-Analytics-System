"""API routes for Executive Summary Agent."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db_session
from backend.app.repositories.dataset_metadata_repository import DatasetMetadataRepository
from backend.app.repositories.dataset_profile_repository import DatasetProfileRepository
from backend.app.repositories.dataset_quality_repository import DatasetQualityRepository
from backend.app.schemas.executive_summary import (
    ExecutiveSummaryRequest,
    ExecutiveSummaryResponse,
)
from backend.app.services.executive_summary_service import ExecutiveSummaryService
from backend.app.services.executive_summary_agent_service import get_executive_summary_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/summary", tags=["Executive Summary"])


@router.post(
    "/generate",
    response_model=ExecutiveSummaryResponse,
    summary="Generate multi-level executive summary from agent results",
)
async def generate_executive_summary(
    request: ExecutiveSummaryRequest,
    summary_service: ExecutiveSummaryService = Depends(get_executive_summary_service),
) -> ExecutiveSummaryResponse:
    """Generate executive narrative, key findings, opportunities, risks, and health score."""
    logger.info("Generating executive summary for request with %d result keys", len(request.results))
    result = summary_service.generate_summary(
        results=request.results,
        metadata=request.metadata,
        profile=request.profile,
        quality=request.quality,
        query=request.query,
    )
    return ExecutiveSummaryResponse(
        summary=result,
        dataset_id=request.dataset_id,
    )


@router.get(
    "/{dataset_id}",
    response_model=ExecutiveSummaryResponse,
    summary="Generate executive summary for a stored dataset",
)
async def get_dataset_executive_summary(
    dataset_id: str,
    db: Session = Depends(get_db_session),
    summary_service: ExecutiveSummaryService = Depends(get_executive_summary_service),
) -> ExecutiveSummaryResponse:
    """Retrieve stored dataset metadata, profile, and quality to generate an executive summary."""
    meta_repo = DatasetMetadataRepository(db)
    meta = meta_repo.get(dataset_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_id}' not found",
        )

    prof_repo = DatasetProfileRepository(db)
    profile = prof_repo.get(dataset_id)

    qual_repo = DatasetQualityRepository(db)
    quality = qual_repo.get(dataset_id)

    metadata_dict = {
        "dataset_id": dataset_id,
        "row_count": meta.row_count,
        "column_count": meta.column_count,
        "column_names": meta.column_names,
        "column_types": meta.column_types,
        "classifications": meta.classifications,
    }

    profile_dict = profile.summary if profile and hasattr(profile, "summary") else {}
    quality_dict = (
        {
            "quality_score": quality.overall_score,
            "completeness": quality.completeness_score,
            "validity": quality.validity_score,
            "uniqueness": quality.uniqueness_score,
        }
        if quality
        else {}
    )


    result = summary_service.generate_summary(
        results={},
        metadata=metadata_dict,
        profile=profile_dict if isinstance(profile_dict, dict) else {},
        quality=quality_dict,
        query=f"Dataset {dataset_id} overview",
    )

    return ExecutiveSummaryResponse(
        summary=result,
        dataset_id=dataset_id,
    )
