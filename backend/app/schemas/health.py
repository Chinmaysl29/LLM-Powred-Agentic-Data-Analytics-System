"""Health endpoint response models."""

from typing import Literal

from pydantic import BaseModel


class DependencyHealth(BaseModel):
    """Health result for one application dependency."""

    status: Literal["healthy", "unhealthy"]
    message: str


class HealthResponse(BaseModel):
    """Detailed service readiness response."""

    success: bool
    status: Literal["healthy", "degraded"]
    application: DependencyHealth
    postgresql: DependencyHealth
    redis: DependencyHealth
    chromadb: DependencyHealth
