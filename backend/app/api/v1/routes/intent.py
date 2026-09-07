"""Intent classification API endpoints for Phase 3.1."""

import logging
from fastapi import APIRouter, Depends, status

from backend.app.schemas.intent import (
    IntentClassificationRequest,
    IntentClassificationResponse,
)
from backend.app.services.intent_classification_service import (
    IntentClassificationService,
    get_intent_classification_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intent", tags=["Intent Classifier"])


@router.post(
    "/classify",
    response_model=IntentClassificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify natural language query into structured intent",
)
async def classify_intent(
    request: IntentClassificationRequest,
    service: IntentClassificationService = Depends(get_intent_classification_service),
) -> IntentClassificationResponse:
    """Analyze incoming user query and return classified intent with confidence and required agents."""
    logger.info("Received intent classification request: %s", request.query[:50])
    return await service.classify(
        query=request.query,
        context=request.context,
        dataset_id=request.dataset_id,
    )
