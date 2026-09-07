"""Phase 12.6.7 — Model Router.

Routes generation and analytics requests based on policy:
Cost-aware, Latency-aware, Provider-specific, and Fallback routing.
"""

from __future__ import annotations

import enum
import logging
from typing import Any, Dict, List, Optional

from backend.model_hub.base import BaseModelProvider, GenerationResult
from backend.model_hub.providers import (
    ClaudeProvider,
    GeminiProvider,
    GroqProvider,
    OpenAIProvider,
)
from backend.model_hub.registry import ModelMetadata, ModelRegistry

logger = logging.getLogger(__name__)


class RoutingPolicy(str, enum.Enum):
    COST_AWARE = "COST_AWARE"
    LATENCY_AWARE = "LATENCY_AWARE"
    PERFORMANCE_FIRST = "PERFORMANCE_FIRST"
    PROVIDER_SPECIFIC = "PROVIDER_SPECIFIC"


class ModelRouter:
    """Intelligent dispatcher selecting the optimal model provider for every request."""

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        providers: Optional[Dict[str, BaseModelProvider]] = None,
    ) -> None:
        self.registry = registry or ModelRegistry()
        self.providers: Dict[str, BaseModelProvider] = providers or {
            "openai": OpenAIProvider(),
            "gemini": GeminiProvider(),
            "claude": ClaudeProvider(),
            "groq": GroqProvider(),
        }
        # Fallback sequence if a requested provider is unavailable
        self.fallback_order = ["groq", "gemini", "openai", "claude"]

    def select_model(
        self,
        policy: RoutingPolicy = RoutingPolicy.LATENCY_AWARE,
        preferred_provider: Optional[str] = None,
        required_capability: Optional[str] = "chat",
    ) -> ModelMetadata:
        """Select best model matching routing policy."""
        active_models = self.registry.list_models()
        if not active_models:
            raise RuntimeError("No active models registered in ModelRegistry.")

        if required_capability:
            candidate_models = [m for m in active_models if required_capability in m.capabilities]
            if candidate_models:
                active_models = candidate_models

        if policy == RoutingPolicy.PROVIDER_SPECIFIC and preferred_provider:
            p_clean = preferred_provider.lower()
            matching = [m for m in active_models if m.provider_name == p_clean]
            if matching:
                return matching[0]

        if policy == RoutingPolicy.COST_AWARE:
            # Lowest combined token price
            return min(active_models, key=lambda m: (m.cost_per_1m_input + m.cost_per_1m_output))

        if policy == RoutingPolicy.LATENCY_AWARE:
            # Lowest average latency
            return min(active_models, key=lambda m: m.avg_latency_ms)

        # Default fallback to first active model
        return active_models[0]

    def route(
        self,
        prompt: str,
        policy: RoutingPolicy = RoutingPolicy.LATENCY_AWARE,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> GenerationResult:
        """Route generation request to the selected or fallback provider."""
        target_provider = provider_name.lower() if provider_name else None
        target_model = model_name

        if not target_provider:
            selected_meta = self.select_model(policy=policy)
            target_provider = selected_meta.provider_name
            target_model = target_model or selected_meta.model_name

        provider = self.providers.get(target_provider)

        # Fallback routing if provider not registered or inactive
        if not provider or not provider.is_active:
            logger.warning("Target provider '%s' unavailable. Executing fallback routing...", target_provider)
            for fb in self.fallback_order:
                if fb != target_provider and fb in self.providers and self.providers[fb].is_active:
                    provider = self.providers[fb]
                    target_model = provider.default_model
                    target_provider = fb
                    break

        if not provider:
            raise RuntimeError("All providers in fallback chain are unavailable.")

        logger.info("Routing request to provider: [%s] model: [%s]", target_provider, target_model)
        return provider.generate(prompt=prompt, model=target_model, **kwargs)
