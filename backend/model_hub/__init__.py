"""Phase 12.6 — AI Model Hub Package.

Exports BaseModelProvider, ModelRegistry, ModelRouter, ModelFailoverEngine,
ModelBenchmarkingEngine, and standard provider adapters.
"""

from backend.model_hub.base import (
    BaseModelProvider,
    EmbeddingResult,
    GenerationResult,
    ProviderHealthResult,
)
from backend.model_hub.benchmark import (
    ModelBenchmarkingEngine,
    ModelScorecard,
)
from backend.model_hub.failover import ModelFailoverEngine
from backend.model_hub.providers import (
    ClaudeProvider,
    GeminiProvider,
    GroqProvider,
    OpenAIProvider,
)
from backend.model_hub.registry import (
    ModelMetadata,
    ModelRegistry,
    ModelStatus,
)
from backend.model_hub.router import (
    ModelRouter,
    RoutingPolicy,
)

__all__ = [
    "BaseModelProvider",
    "GenerationResult",
    "EmbeddingResult",
    "ProviderHealthResult",
    "ModelMetadata",
    "ModelStatus",
    "ModelRegistry",
    "OpenAIProvider",
    "GeminiProvider",
    "ClaudeProvider",
    "GroqProvider",
    "ModelRouter",
    "RoutingPolicy",
    "ModelFailoverEngine",
    "ModelBenchmarkingEngine",
    "ModelScorecard",
]
