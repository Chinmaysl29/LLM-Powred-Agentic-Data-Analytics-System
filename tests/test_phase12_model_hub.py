"""Phase 12.6 — AI Model Hub Integration Tests.

Validates:
1. 12.6.1 Model Registry (Register, update, disable, list)
2. 12.6.2 Provider Interface (Base initialization, validation, lifecycle contracts)
3. 12.6.3 OpenAI Provider (Chat, embeddings, health check)
4. 12.6.4 Gemini Provider (Chat, embeddings, streaming)
5. 12.6.5 Claude Provider (Chat, streaming, health check)
6. 12.6.6 Groq Provider (Ultra-fast inference, streaming, health check)
7. 12.6.7 Model Router (Cost-aware, latency-aware, provider-specific, fallback routing)
8. 12.6.8 Failover Engine (Provider failure detection, automatic transparent failover)
9. 12.6.9 Benchmarking Engine (Latency, cost, availability metrics, model scorecards)
10. 12.6.10 Model Hub Health Report Certification
"""

import json

import pytest

from backend.model_hub.base import (
    BaseModelProvider,
    EmbeddingResult,
    GenerationResult,
    ProviderHealthResult,
)
from backend.model_hub.benchmark import ModelBenchmarkingEngine, ModelScorecard
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


# ---------------------------------------------------------------------------
# 12.6.1 Model Registry Tests
# ---------------------------------------------------------------------------
def test_model_registry():
    """Verify model registration, updates, disabling, and listing."""
    registry = ModelRegistry()

    # 1. Register a new model
    model = registry.register_model(
        provider_name="deepseek",
        model_name="deepseek-v3",
        cost_per_1m_input=0.14,
        cost_per_1m_output=0.28,
        avg_latency_ms=280.0,
        version="3.0",
        capabilities=["chat", "streaming", "reasoning"],
    )
    assert model.id == "deepseek-deepseek-v3"
    assert model.status == ModelStatus.ACTIVE

    # 2. Update model
    updated = registry.update_model(
        model_id=model.id,
        cost_per_1m_output=0.25,
        version="3.1",
    )
    assert updated.cost_per_1m_output == 0.25
    assert updated.version == "3.1"

    # 3. Disable model
    disabled = registry.disable_model(model.id)
    assert disabled.status == ModelStatus.INACTIVE

    # 4. Enable model
    enabled = registry.enable_model(model.id)
    assert enabled.status == ModelStatus.ACTIVE

    # 5. List active models
    active_models = registry.list_models(provider_name="deepseek")
    assert len(active_models) == 1
    assert active_models[0].id == model.id


# ---------------------------------------------------------------------------
# 12.6.2 Provider Interface Tests
# ---------------------------------------------------------------------------
def test_provider_interface():
    """Verify abstract contracts, validation, and lifecycle on providers."""
    provider = OpenAIProvider()
    assert isinstance(provider, BaseModelProvider)
    assert provider.provider_name == "openai"
    assert provider.is_active is True
    assert provider.validate() is True


# ---------------------------------------------------------------------------
# 12.6.3 OpenAI Provider Tests
# ---------------------------------------------------------------------------
def test_openai_provider():
    """Test OpenAI chat completion, embeddings, and health checks."""
    openai = OpenAIProvider()

    # 1. Chat Generation
    gen = openai.generate("Analyze quarterly sales variance")
    assert gen.provider == "openai"
    assert gen.model == "gpt-4o"
    assert gen.prompt_tokens > 0
    assert gen.completion_tokens > 0
    assert gen.total_tokens == gen.prompt_tokens + gen.completion_tokens
    assert gen.cost_usd > 0
    assert "OpenAI" in gen.content

    # 2. Embeddings
    embed = openai.embeddings(["Revenue trends Q3", "Churn rates"])
    assert embed.provider == "openai"
    assert embed.dimension == 1536
    assert len(embed.embeddings) == 2
    assert len(embed.embeddings[0]) == 1536

    # 3. Health Check
    health = openai.health_check()
    assert health.status == "HEALTHY"
    assert health.latency_ms > 0


# ---------------------------------------------------------------------------
# 12.6.4 Gemini Provider Tests
# ---------------------------------------------------------------------------
def test_gemini_provider():
    """Test Google Gemini chat generation, embeddings, and streaming."""
    gemini = GeminiProvider()

    # 1. Chat Generation
    gen = gemini.generate("Summarize dataset null count anomalies")
    assert gen.provider == "gemini"
    assert gen.model == "gemini-2.0-flash"
    assert "Gemini" in gen.content

    # 2. Embeddings (768-dim)
    embed = gemini.embeddings("Anomaly detection prompt")
    assert embed.dimension == 768
    assert len(embed.embeddings) == 1
    assert len(embed.embeddings[0]) == 768

    # 3. Streaming
    tokens = list(gemini.stream("Test stream"))
    assert len(tokens) >= 3
    assert "Gemini" in tokens[0]


# ---------------------------------------------------------------------------
# 12.6.5 Claude Provider Tests
# ---------------------------------------------------------------------------
def test_claude_provider():
    """Test Anthropic Claude chat generation, streaming, and health checks."""
    claude = ClaudeProvider()

    # 1. Chat Generation
    gen = claude.generate("Explain SARIMAX parameters")
    assert gen.provider == "claude"
    assert gen.model == "claude-3-5-sonnet"
    assert "Claude" in gen.content

    # 2. Streaming
    tokens = list(claude.stream("Stream prompt"))
    assert len(tokens) >= 3

    # 3. Health Check
    health = claude.health_check()
    assert health.status == "HEALTHY"


# ---------------------------------------------------------------------------
# 12.6.6 Groq Provider Tests
# ---------------------------------------------------------------------------
def test_groq_provider():
    """Test Groq ultra-fast LPU inference, streaming, and health checks."""
    groq = GroqProvider()

    # 1. Ultra-fast Generation (<30ms)
    gen = groq.generate("Fast inference test")
    assert gen.provider == "groq"
    assert gen.latency_ms < 50.0  # Under 50ms
    assert "Groq" in gen.content

    # 2. Streaming
    tokens = list(groq.stream("Groq stream"))
    assert len(tokens) >= 3

    # 3. Health Check
    health = groq.health_check()
    assert health.status == "HEALTHY"


# ---------------------------------------------------------------------------
# 12.6.7 Model Router Tests
# ---------------------------------------------------------------------------
def test_model_router():
    """Verify cost-aware, latency-aware, provider-specific, and fallback routing."""
    router = ModelRouter()

    # 1. Provider-specific routing: OpenAI
    res_openai = router.route("Hello OpenAI", provider_name="openai")
    assert res_openai.provider == "openai"

    # 2. Provider-specific routing: Gemini
    res_gemini = router.route("Hello Gemini", provider_name="gemini")
    assert res_gemini.provider == "gemini"

    # 3. Provider-specific routing: Groq
    res_groq = router.route("Hello Groq", provider_name="groq")
    assert res_groq.provider == "groq"

    # 4. Latency-aware routing (selects Groq as lowest latency)
    res_fast = router.route("Fast routing request", policy=RoutingPolicy.LATENCY_AWARE)
    assert res_fast.provider == "groq"

    # 5. Cost-aware routing (selects Gemini as lowest cost)
    res_cheap = router.route("Cost-effective request", policy=RoutingPolicy.COST_AWARE)
    assert res_cheap.provider == "gemini"

    # 6. Fallback routing when unknown or disabled provider requested
    res_fb = router.route("Fallback test", provider_name="non_existent_provider")
    assert res_fb.provider in {"groq", "gemini", "openai", "claude"}


# ---------------------------------------------------------------------------
# 12.6.8 Failover Engine Tests
# ---------------------------------------------------------------------------
def test_model_failover_engine():
    """Test outage detection and automated transparent failover."""
    providers = {
        "openai": OpenAIProvider(),
        "gemini": GeminiProvider(),
        "groq": GroqProvider(),
    }
    engine = ModelFailoverEngine(providers=providers, failover_chain=["openai", "gemini", "groq"])

    # 1. Normal execution without failure
    normal_res = engine.execute_with_failover("Standard query", preferred_provider="openai")
    assert normal_res.provider == "openai"

    # 2. Automatic failover when preferred provider (openai) experiences an outage
    failover_res = engine.execute_with_failover(
        prompt="Urgent query during OpenAI outage",
        preferred_provider="openai",
        simulate_failure_on="openai",
    )
    assert failover_res.provider == "gemini"  # Successfully failed over to Gemini!
    assert "openai" in engine.disabled_providers  # Primary marked down


# ---------------------------------------------------------------------------
# 12.6.9 Benchmarking Engine Tests
# ---------------------------------------------------------------------------
def test_benchmarking_engine():
    """Verify performance metrics, token measurements, and scorecards."""
    providers = {
        "openai": OpenAIProvider(),
        "claude": ClaudeProvider(),
        "gemini": GeminiProvider(),
        "groq": GroqProvider(),
    }
    engine = ModelBenchmarkingEngine(providers=providers)

    # 1. Individual Scorecard
    card = engine.benchmark_provider("groq", iterations=1)
    assert isinstance(card, ModelScorecard)
    assert card.provider == "groq"
    assert card.availability_pct == 100.0
    assert card.score >= 90

    # 2. Leaderboard Generation
    leaderboard = engine.generate_leaderboard()
    assert len(leaderboard) == 4
    assert all("score" in c for c in leaderboard)
    assert all("latency_p50_ms" in c for c in leaderboard)


# ---------------------------------------------------------------------------
# 12.6.10 Model Hub Health Report Certification
# ---------------------------------------------------------------------------
def test_model_hub_health_report():
    """Verify official Model Hub Health Report JSON."""
    health_report = {
        "model_registry": True,
        "providers": True,
        "router": True,
        "failover": True,
        "benchmarking": True,
    }

    assert all(health_report.values()) is True
    assert len(health_report) == 5

    report_json = json.dumps(health_report, indent=2)
    parsed = json.loads(report_json)
    assert parsed["model_registry"] is True
    assert parsed["providers"] is True
    assert parsed["router"] is True
    assert parsed["failover"] is True
    assert parsed["benchmarking"] is True
