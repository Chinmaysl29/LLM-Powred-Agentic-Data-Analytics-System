"""Natural-language analytics chat API (Phase 17.1)."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database.postgres import get_db_session
from backend.app.services.data_retrieval_service import DataRetrievalService
from backend.app.services.intent_classification_service import IntentClassificationService, get_intent_classification_service
from backend.app.services.natural_language_analytics import NaturalLanguageAnalyticsService
from backend.app.services.orchestrator_service import OrchestratorService
from backend.app.services.storage_service import StorageService, get_storage_service
from backend.monitoring.prometheus_metrics import platform_metrics

router = APIRouter(prefix="/chat", tags=["Natural Language Analytics"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    dataset_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    confidence: float = Field(ge=0, le=1)
    execution_time: float
    data: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str | None = None
    actionable: list[str] = Field(default_factory=list)


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    intent_service: IntentClassificationService = Depends(get_intent_classification_service),
    db: Session | None = Depends(get_db_session),
    storage: StorageService = Depends(get_storage_service),
) -> ChatResponse:
    started = perf_counter()
    classification = await intent_service.classify(payload.message, dataset_id=payload.dataset_id)
    analytics = NaturalLanguageAnalyticsService(DataRetrievalService(db, storage) if db is not None else None)
    if analytics.is_analytics_query(payload.message) and payload.dataset_id:
        result = await analytics.analyze(payload.message, dataset_id=payload.dataset_id)
        intent = "analytics"
        confidence = max(classification.confidence, 0.85)
    elif analytics.is_analytics_query(payload.message):
        result = await analytics.analyze(payload.message)
        intent, confidence = "analytics", max(classification.confidence, 0.85)
    else:
        orchestrator = OrchestratorService(intent_classifier=intent_service, db=db)
        outcome = await orchestrator.execute(payload.message, dataset_id=payload.dataset_id)
        result = {"answer": outcome.summary, "data": [], "explanation": "Processed through the configured analytics workflow.", "actionable": []}
        intent, confidence = outcome.intent, classification.confidence
    platform_metrics.record_agent_execution("natural_language_analytics", "success")
    return ChatResponse(intent=intent, confidence=confidence, execution_time=round(perf_counter() - started, 4), **result)
