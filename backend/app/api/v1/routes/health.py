"""Application dependency health endpoint."""

from fastapi import APIRouter, Request

from backend.app.schemas.health import DependencyHealth, HealthResponse
from backend.monitoring.prometheus_metrics import platform_metrics

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Return application and dependency status without exposing implementation details."""
    postgres_ok, postgres_message = await request.app.state.postgres.health_check()
    redis_ok, redis_message = await request.app.state.redis.health_check()
    chroma_ok, chroma_message = await request.app.state.chroma.health_check()
    dependencies_healthy = postgres_ok and redis_ok and chroma_ok
    platform_metrics.set_dependency_health("postgres", postgres_ok)
    platform_metrics.set_dependency_health("redis", redis_ok)
    platform_metrics.set_dependency_health("chromadb", chroma_ok)

    return HealthResponse(
        success=dependencies_healthy,
        status="healthy" if dependencies_healthy else "degraded",
        application=DependencyHealth(status="healthy", message="Application is running"),
        postgresql=DependencyHealth(
            status="healthy" if postgres_ok else "unhealthy", message=postgres_message
        ),
        redis=DependencyHealth(status="healthy" if redis_ok else "unhealthy", message=redis_message),
        chromadb=DependencyHealth(status="healthy" if chroma_ok else "unhealthy", message=chroma_message),
    )
