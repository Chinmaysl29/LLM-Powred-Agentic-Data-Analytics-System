"""FastAPI application factory and infrastructure lifecycle management."""

import logging
from contextlib import asynccontextmanager
from inspect import isawaitable
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import router as api_v1_router
from backend.app.core.config import get_settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logging import configure_logging
from backend.app.database.chromadb import ChromaDatabase
from backend.app.database.postgres import PostgresDatabase
from backend.app.database.redis import RedisCache
from backend.app.middleware.request_id import RequestIDMiddleware
from backend.app.middleware.request_logging import RequestLoggingMiddleware
from backend.app.middleware.response_time import ResponseTimeMiddleware
from backend.app.middleware.metrics import PrometheusMetricsMiddleware
from backend.app.middleware.audit import AuditTrailMiddleware
from backend.app.middleware.tracing import TracingMiddleware
from backend.monitoring.prometheus_metrics import platform_metrics

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and safely release infrastructure clients for one process."""
    settings = get_settings()
    configure_logging(settings)
    app.state.postgres = PostgresDatabase(settings)
    app.state.redis = RedisCache(settings)
    app.state.chroma = ChromaDatabase(settings)
    logger.info("Application startup initiated environment=%s", settings.environment)

    for dependency_name, connector in (
        ("PostgreSQL", app.state.postgres.connect),
        ("Redis", app.state.redis.connect),
        ("ChromaDB", app.state.chroma.connect),
    ):
        try:
            result = connector()
            if isawaitable(result):
                await result
        except Exception:
            logger.warning("%s is unavailable at startup; health checks will retry", dependency_name, exc_info=True)

    yield

    await app.state.redis.close()
    await app.state.chroma.close()
    app.state.postgres.close()
    logging.shutdown()


def create_app() -> FastAPI:
    """Construct the configured FastAPI application."""
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(ResponseTimeMiddleware)
    application.add_middleware(PrometheusMetricsMiddleware)
    application.add_middleware(AuditTrailMiddleware)
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(RequestIDMiddleware)
    application.add_middleware(TracingMiddleware)
    application.include_router(api_v1_router)

    @application.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=platform_metrics.render(), media_type="text/plain; version=0.0.4")

    register_exception_handlers(application)
    return application


app = create_app()
