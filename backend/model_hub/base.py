"""Phase 12.6.2 — Model Provider Interface.

Abstract base contract for AI model providers supporting text generation,
token streaming, vector embeddings, and real-time health checks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Iterator, List, Optional
import uuid

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    id: str = field(default_factory=lambda: f"gen-{uuid.uuid4().hex[:10]}")
    provider: str = ""
    model: str = ""
    content: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    finish_reason: str = "stop"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider,
            "model": self.model,
            "content": self.content,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "finish_reason": self.finish_reason,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class EmbeddingResult:
    provider: str
    model: str
    embeddings: List[List[float]]
    dimension: int
    tokens_used: int
    latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "dimension": self.dimension,
            "count": len(self.embeddings),
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
        }


@dataclass
class ProviderHealthResult:
    provider: str
    status: str  # "HEALTHY", "DEGRADED", "UNHEALTHY"
    latency_ms: float
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseModelProvider(ABC):
    """Abstract interface defining required methods for all LLM and embedding providers."""

    def __init__(self, provider_name: str, default_model: str, config: Optional[Dict[str, Any]] = None) -> None:
        self.provider_name = provider_name
        self.default_model = default_model
        self.config = config or {}
        self._is_active = True

    @property
    def is_active(self) -> bool:
        return self._is_active

    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> GenerationResult:
        """Execute text or chat generation request."""
        pass

    @abstractmethod
    def stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Yield generated text tokens iteratively."""
        pass

    @abstractmethod
    def embeddings(
        self,
        texts: List[str] | str,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> EmbeddingResult:
        """Generate dense vector embeddings."""
        pass

    @abstractmethod
    def health_check(self) -> ProviderHealthResult:
        """Ping provider API endpoint to evaluate latency and status."""
        pass

    def validate(self) -> bool:
        """Verify presence of API configuration or operational credentials."""
        return True
