"""Phase 12.6.1 — Model Registry.

Catalog and inventory management for AI models across providers, tracking
versions, token pricing, latency benchmarks, capabilities, and active statuses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import enum
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class ModelStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DEPRECATED = "DEPRECATED"


@dataclass
class ModelMetadata:
    id: str = field(default_factory=lambda: f"mdl-{uuid.uuid4().hex[:8]}")
    provider_name: str = ""
    model_name: str = ""
    version: str = "1.0.0"
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0
    avg_latency_ms: float = 0.0
    capabilities: List[str] = field(default_factory=lambda: ["chat", "streaming"])
    status: ModelStatus = ModelStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "provider_name": self.provider_name,
            "model_name": self.model_name,
            "version": self.version,
            "cost_per_1m_input": self.cost_per_1m_input,
            "cost_per_1m_output": self.cost_per_1m_output,
            "avg_latency_ms": self.avg_latency_ms,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ModelRegistry:
    """Registry maintaining active catalog of available enterprise AI models."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelMetadata] = {}
        self._seed_default_catalog()

    def _seed_default_catalog(self) -> None:
        defaults = [
            ModelMetadata(
                id="gpt-4o",
                provider_name="openai",
                model_name="gpt-4o",
                version="2024-11-20",
                cost_per_1m_input=2.50,
                cost_per_1m_output=10.00,
                avg_latency_ms=450.0,
                capabilities=["chat", "streaming", "function_calling", "vision"],
            ),
            ModelMetadata(
                id="text-embedding-3-small",
                provider_name="openai",
                model_name="text-embedding-3-small",
                version="3.0",
                cost_per_1m_input=0.02,
                cost_per_1m_output=0.0,
                avg_latency_ms=75.0,
                capabilities=["embeddings"],
            ),
            ModelMetadata(
                id="gemini-2-0-flash",
                provider_name="gemini",
                model_name="gemini-2.0-flash",
                version="2.0",
                cost_per_1m_input=0.10,
                cost_per_1m_output=0.40,
                avg_latency_ms=210.0,
                capabilities=["chat", "streaming", "embeddings", "multimodal"],
            ),
            ModelMetadata(
                id="claude-3-5-sonnet",
                provider_name="claude",
                model_name="claude-3-5-sonnet",
                version="20241022",
                cost_per_1m_input=3.00,
                cost_per_1m_output=15.00,
                avg_latency_ms=520.0,
                capabilities=["chat", "streaming", "code_generation"],
            ),
            ModelMetadata(
                id="llama-3-3-70b-versatile",
                provider_name="groq",
                model_name="llama-3.3-70b-versatile",
                version="3.3",
                cost_per_1m_input=0.59,
                cost_per_1m_output=0.79,
                avg_latency_ms=85.0,
                capabilities=["chat", "streaming", "ultra_fast_inference"],
            ),
        ]
        for m in defaults:
            self._models[m.id] = m

    def register_model(
        self,
        provider_name: str,
        model_name: str,
        cost_per_1m_input: float,
        cost_per_1m_output: float,
        avg_latency_ms: float,
        version: str = "1.0.0",
        capabilities: Optional[List[str]] = None,
        model_id: Optional[str] = None,
    ) -> ModelMetadata:
        """Register a new model in the registry."""
        clean_provider = provider_name.strip().lower()
        clean_model = model_name.strip()
        mid = model_id or f"{clean_provider}-{clean_model}"

        model = ModelMetadata(
            id=mid,
            provider_name=clean_provider,
            model_name=clean_model,
            version=version,
            cost_per_1m_input=cost_per_1m_input,
            cost_per_1m_output=cost_per_1m_output,
            avg_latency_ms=avg_latency_ms,
            capabilities=capabilities or ["chat", "streaming"],
            status=ModelStatus.ACTIVE,
        )
        self._models[mid] = model
        logger.info("Registered model '%s' (provider=%s)", mid, clean_provider)
        return model

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Fetch model metadata by ID."""
        return self._models.get(model_id)

    def update_model(
        self,
        model_id: str,
        version: Optional[str] = None,
        cost_per_1m_input: Optional[float] = None,
        cost_per_1m_output: Optional[float] = None,
        avg_latency_ms: Optional[float] = None,
        status: Optional[ModelStatus | str] = None,
    ) -> ModelMetadata:
        """Update existing model pricing, latency, or version."""
        model = self.get_model(model_id)
        if not model:
            raise KeyError(f"Model '{model_id}' not found in registry.")

        if version:
            model.version = version
        if cost_per_1m_input is not None:
            model.cost_per_1m_input = cost_per_1m_input
        if cost_per_1m_output is not None:
            model.cost_per_1m_output = cost_per_1m_output
        if avg_latency_ms is not None:
            model.avg_latency_ms = avg_latency_ms
        if status:
            model.status = ModelStatus(status) if isinstance(status, str) else status

        model.updated_at = datetime.now(timezone.utc)
        logger.info("Updated model '%s'", model_id)
        return model

    def disable_model(self, model_id: str) -> ModelMetadata:
        """Deactivate a model."""
        return self.update_model(model_id, status=ModelStatus.INACTIVE)

    def enable_model(self, model_id: str) -> ModelMetadata:
        """Activate a model."""
        return self.update_model(model_id, status=ModelStatus.ACTIVE)

    def list_models(
        self,
        provider_name: Optional[str] = None,
        status: Optional[ModelStatus | str] = ModelStatus.ACTIVE,
    ) -> List[ModelMetadata]:
        """List registered models with optional filtering."""
        models = list(self._models.values())
        if provider_name:
            p_clean = provider_name.strip().lower()
            models = [m for m in models if m.provider_name == p_clean]
        if status:
            stat_enum = ModelStatus(status) if isinstance(status, str) else status
            models = [m for m in models if m.status == stat_enum]
        return models
