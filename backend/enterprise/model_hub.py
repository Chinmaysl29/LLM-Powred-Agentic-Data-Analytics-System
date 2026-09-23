"""Phase 12.6 — AI Model Hub

Provides enterprise LLM and model governance, multi-provider model routing
(cost-optimized, latency-optimized, reasoning-first, compliance-first),
tenant token spend budgets, and fine-tuned adapter registries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    META = "meta"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    LOCAL = "local"


class RoutingStrategy(str, Enum):
    COST_OPTIMIZED = "cost_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    REASONING_FIRST = "reasoning_first"
    COMPLIANCE_LOCAL = "compliance_local"


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: ModelProvider
    context_window: int
    cost_per_1m_input: float
    cost_per_1m_output: float
    avg_latency_ms: float
    reasoning_score: float  # 0 to 100
    is_fine_tune_ready: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider.value,
            "context_window": self.context_window,
            "cost_per_1m_input": self.cost_per_1m_input,
            "cost_per_1m_output": self.cost_per_1m_output,
            "avg_latency_ms": self.avg_latency_ms,
            "reasoning_score": self.reasoning_score,
            "is_fine_tune_ready": self.is_fine_tune_ready,
        }


@dataclass
class TenantModelBudget:
    tenant_id: str
    monthly_budget_usd: float = 500.0
    current_spend_usd: float = 0.0
    total_tokens_used: int = 0
    hard_limit_enforced: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "monthly_budget_usd": self.monthly_budget_usd,
            "current_spend_usd": round(self.current_spend_usd, 4),
            "total_tokens_used": self.total_tokens_used,
            "budget_utilization_pct": round((self.current_spend_usd / max(0.01, self.monthly_budget_usd)) * 100, 2),
            "hard_limit_enforced": self.hard_limit_enforced,
        }


@dataclass
class FineTunedAdapter:
    id: str
    tenant_id: str
    name: str
    base_model_id: str
    weights_uri: str
    status: str = "READY"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "base_model_id": self.base_model_id,
            "weights_uri": self.weights_uri,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


class ModelHub:
    """Singleton registry and intelligent model router for enterprise LLM operations."""

    _instance: Optional[ModelHub] = None

    def __new__(cls) -> ModelHub:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._models: Dict[str, ModelInfo] = {}
            cls._instance._budgets: Dict[str, TenantModelBudget] = {}
            cls._instance._adapters: Dict[str, FineTunedAdapter] = {}
            cls._instance._init_models()
        return cls._instance

    def _init_models(self) -> None:
        """Seed certified LLM catalog."""
        models = [
            ModelInfo(
                id="gpt-4o",
                name="OpenAI GPT-4o",
                provider=ModelProvider.OPENAI,
                context_window=128000,
                cost_per_1m_input=2.50,
                cost_per_1m_output=10.00,
                avg_latency_ms=450.0,
                reasoning_score=94.5,
                is_fine_tune_ready=True,
            ),
            ModelInfo(
                id="claude-3-5-sonnet",
                name="Anthropic Claude 3.5 Sonnet",
                provider=ModelProvider.ANTHROPIC,
                context_window=200000,
                cost_per_1m_input=3.00,
                cost_per_1m_output=15.00,
                avg_latency_ms=520.0,
                reasoning_score=96.0,
            ),
            ModelInfo(
                id="gemini-2-0-flash",
                name="Google Gemini 2.0 Flash",
                provider=ModelProvider.GOOGLE,
                context_window=1048576,
                cost_per_1m_input=0.10,
                cost_per_1m_output=0.40,
                avg_latency_ms=210.0,
                reasoning_score=89.0,
            ),
            ModelInfo(
                id="llama-3-3-70b",
                name="Meta Llama 3.3 70B Versatile",
                provider=ModelProvider.META,
                context_window=131072,
                cost_per_1m_input=0.59,
                cost_per_1m_output=0.79,
                avg_latency_ms=280.0,
                reasoning_score=90.5,
                is_fine_tune_ready=True,
            ),
            ModelInfo(
                id="deepseek-v3",
                name="DeepSeek V3 MoE",
                provider=ModelProvider.DEEPSEEK,
                context_window=64000,
                cost_per_1m_input=0.14,
                cost_per_1m_output=0.28,
                avg_latency_ms=310.0,
                reasoning_score=92.0,
            ),
            ModelInfo(
                id="local-all-minilm",
                name="On-Premises Local Sentence Transformer",
                provider=ModelProvider.LOCAL,
                context_window=512,
                cost_per_1m_input=0.0,
                cost_per_1m_output=0.0,
                avg_latency_ms=35.0,
                reasoning_score=75.0,
            ),
        ]
        for m in models:
            self._models[m.id] = m

    def get_catalog(self) -> List[ModelInfo]:
        """Return all available models."""
        return list(self._models.values())

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Retrieve model metadata."""
        return self._models.get(model_id)

    def route_request(self, strategy: RoutingStrategy) -> ModelInfo:
        """Route to the optimal model based on policy."""
        models = list(self._models.values())
        if strategy == RoutingStrategy.COST_OPTIMIZED:
            # Lowest output cost (excluding local 0.0 unless specified)
            cloud_models = [m for m in models if m.provider != ModelProvider.LOCAL]
            return min(cloud_models, key=lambda m: (m.cost_per_1m_input + m.cost_per_1m_output))
        elif strategy == RoutingStrategy.LATENCY_OPTIMIZED:
            # Lowest latency
            return min(models, key=lambda m: m.avg_latency_ms)
        elif strategy == RoutingStrategy.REASONING_FIRST:
            # Highest reasoning capability
            return max(models, key=lambda m: m.reasoning_score)
        elif strategy == RoutingStrategy.COMPLIANCE_LOCAL:
            # Air-gapped on-prem model
            locals_list = [m for m in models if m.provider == ModelProvider.LOCAL]
            return locals_list[0] if locals_list else models[0]
        return models[0]

    def set_budget(self, tenant_id: str, monthly_budget_usd: float, hard_limit: bool = True) -> TenantModelBudget:
        """Configure monthly spending threshold for a tenant."""
        budget = self._budgets.get(tenant_id)
        if not budget:
            budget = TenantModelBudget(
                tenant_id=tenant_id,
                monthly_budget_usd=monthly_budget_usd,
                hard_limit_enforced=hard_limit,
            )
            self._budgets[tenant_id] = budget
        else:
            budget.monthly_budget_usd = monthly_budget_usd
            budget.hard_limit_enforced = hard_limit
        return budget

    def get_budget(self, tenant_id: str) -> TenantModelBudget:
        """Fetch budget status, provisioning defaults if needed."""
        if tenant_id not in self._budgets:
            self._budgets[tenant_id] = TenantModelBudget(tenant_id=tenant_id)
        return self._budgets[tenant_id]

    def record_usage(
        self,
        tenant_id: str,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Dict[str, Any]:
        """Record model token consumption and compute financial cost."""
        model = self.get_model(model_id)
        if not model:
            raise KeyError(f"Model '{model_id}' not found")

        budget = self.get_budget(tenant_id)

        input_cost = (prompt_tokens / 1_000_000.0) * model.cost_per_1m_input
        output_cost = (completion_tokens / 1_000_000.0) * model.cost_per_1m_output
        total_cost = input_cost + output_cost

        budget.current_spend_usd += total_cost
        budget.total_tokens_used += (prompt_tokens + completion_tokens)

        exceeded = budget.current_spend_usd > budget.monthly_budget_usd
        return {
            "tenant_id": tenant_id,
            "model_id": model_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": round(total_cost, 6),
            "total_spend_usd": round(budget.current_spend_usd, 4),
            "budget_exceeded": exceeded,
        }

    def register_adapter(
        self,
        tenant_id: str,
        name: str,
        base_model_id: str,
        weights_uri: str,
    ) -> FineTunedAdapter:
        """Register custom LoRA / fine-tuned weights for an enterprise client."""
        adapter_id = f"adp-{uuid.uuid4().hex[:12]}"
        adapter = FineTunedAdapter(
            id=adapter_id,
            tenant_id=tenant_id,
            name=name,
            base_model_id=base_model_id,
            weights_uri=weights_uri,
        )
        self._adapters[adapter_id] = adapter
        return adapter

    def list_adapters(self, tenant_id: str) -> List[FineTunedAdapter]:
        """List fine-tuned adapters registered by a tenant."""
        return [a for a in self._adapters.values() if a.tenant_id == tenant_id]

    def reset(self) -> None:
        """Reset storage for testing."""
        self._budgets.clear()
        self._adapters.clear()
        self._models.clear()
        self._init_models()
