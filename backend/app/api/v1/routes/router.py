"""Aggregate version 1 feature routes at one gateway boundary."""

from fastapi import APIRouter

from backend.app.api.v1.routes.auth import router as auth_router
from backend.app.api.v1.routes.datasets import router as datasets_router
from backend.app.api.v1.routes.eda import router as eda_router
from backend.app.api.v1.routes.health import router as health_router
from backend.app.api.v1.routes.intent import router as intent_router
from backend.app.api.v1.routes.orchestrator import router as orchestrator_router
from backend.app.api.v1.routes.planner import router as planner_router
from backend.app.api.v1.routes.retrieval import router as retrieval_router
from backend.app.api.v1.routes.statistics import router as statistics_router
from backend.app.api.v1.routes.validation import router as validation_router
from backend.app.api.v1.routes.executive_summary import router as summary_router
from backend.app.api.v1.routes.schema_reader import router as schema_router
from backend.app.api.v1.routes.sql_guardrails import router as sql_guardrails_router
from backend.app.api.v1.routes.document_loader import router as document_loader_router
from backend.app.api.v1.routes.rag import router as rag_router
from backend.app.api.v1.routes.forecasting import router as forecasting_router
from backend.app.api.v1.routes.operations import router as operations_router
from backend.app.api.v1.routes.enterprise import router as enterprise_router
from backend.app.api.v1.routes.workspaces import router as workspaces_router
from backend.app.api.v1.routes.autonomous import router as autonomous_router
from backend.app.api.v1.routes.audit import router as audit_router
from backend.app.api.v1.routes.chat import router as chat_router


router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(datasets_router)
router.include_router(intent_router)
router.include_router(orchestrator_router)
router.include_router(planner_router)
router.include_router(retrieval_router)
router.include_router(eda_router)
router.include_router(statistics_router)
router.include_router(validation_router)
router.include_router(summary_router)
router.include_router(schema_router)
router.include_router(sql_guardrails_router)
router.include_router(document_loader_router)
router.include_router(rag_router)
router.include_router(forecasting_router)
router.include_router(operations_router)
router.include_router(enterprise_router)
router.include_router(workspaces_router)
router.include_router(autonomous_router)
router.include_router(audit_router)
router.include_router(chat_router)

