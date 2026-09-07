"""Cost Optimization Engine (Phase 11.7).

Monitors and controls multi-model and infrastructure spending:
- OpenAI (GPT-4o, GPT-3.5)
- Groq (LLaMA-3)
- Google Gemini (Gemini 1.5 Pro / Flash)
- Vectorstore & Embedding costs (ChromaDB / text-embedding-3-small)
- Storage & Compute consumption

Analyzes spend patterns and generates automated cost-saving recommendations.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CostCategory(str, Enum):
    OPENAI = "openai"
    GROQ = "groq"
    GEMINI = "gemini"
    EMBEDDINGS = "embeddings"
    STORAGE = "storage"


@dataclass
class CostRecord:
    category: CostCategory
    units: float  # tokens or gigabytes
    estimated_cost_usd: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class CostOptimizationEngine:
    """Enterprise AI Spend & Infrastructure Cost Optimizer."""

    # Reference pricing per million tokens or per GB-month
    UNIT_PRICING = {
        CostCategory.OPENAI: 5.00 / 1_000_000,      # ~$5 per 1M blended GPT-4o tokens
        CostCategory.GROQ: 0.50 / 1_000_000,        # ~$0.50 per 1M tokens
        CostCategory.GEMINI: 0.35 / 1_000_000,      # ~$0.35 per 1M tokens
        CostCategory.EMBEDDINGS: 0.02 / 1_000_000,  # ~$0.02 per 1M embedding tokens
        CostCategory.STORAGE: 0.023,                # ~$0.023 per GB/mo
    }

    def __init__(self, monthly_budget_usd: float = 1000.0) -> None:
        self.monthly_budget_usd = monthly_budget_usd
        self._records: List[CostRecord] = []

    def record_usage(
        self,
        category: CostCategory | str,
        units: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record model token usage or storage consumption."""
        cat = CostCategory(category.lower()) if isinstance(category, str) else category
        rate = self.UNIT_PRICING.get(cat, 0.0)
        cost = round(units * rate, 4)

        record = CostRecord(
            category=cat,
            units=units,
            estimated_cost_usd=cost,
            metadata=metadata or {},
        )
        self._records.append(record)
        return {
            "category": cat.value,
            "units": units,
            "estimated_cost_usd": cost,
            "timestamp": record.timestamp,
        }

    def get_cost_analysis(self) -> Dict[str, Any]:
        """Aggregate total and category spend, and generate actionable savings recommendations."""
        category_spend: Dict[str, float] = {c.value: 0.0 for c in CostCategory}
        category_units: Dict[str, float] = {c.value: 0.0 for c in CostCategory}

        for r in self._records:
            category_spend[r.category.value] += r.estimated_cost_usd
            category_units[r.category.value] += r.units

        total_cost = sum(category_spend.values())
        recommendations: List[Dict[str, Any]] = []
        potential_savings = 0.0

        # Rule 1: High OpenAI Spend -> Migrate to Groq or Gemini Flash for classification
        openai_spend = category_spend.get(CostCategory.OPENAI.value, 0.0)
        if openai_spend > 200.0 or (total_cost > 0 and (openai_spend / total_cost) > 0.5):
            savings = round(openai_spend * 0.65, 2)
            potential_savings += savings
            recommendations.append({
                "id": "REC_LLM_ROUTING",
                "title": "Migrate Routine Queries to High-Throughput Engine (Groq / Gemini)",
                "description": f"OpenAI accounts for ${openai_spend:.2f} of total spend. Routing simple SQL/intent queries to Groq can save up to ${savings:.2f}/mo.",
                "potential_savings_usd": savings,
                "urgency": "HIGH" if openai_spend > 500 else "MEDIUM",
            })

        # Rule 2: High Embedding / RAG Spend -> Prompt and Vector Caching
        embedding_spend = category_spend.get(CostCategory.EMBEDDINGS.value, 0.0)
        if embedding_spend > 50.0:
            savings = round(embedding_spend * 0.40, 2)
            potential_savings += savings
            recommendations.append({
                "id": "REC_VECTOR_CACHE",
                "title": "Enable Redis Semantic Query Caching",
                "description": "High frequency of repeated embedding calls detected. Caching top 20% queries will reduce embedding spend by 40%.",
                "potential_savings_usd": savings,
                "urgency": "MEDIUM",
            })

        # Rule 3: Storage Optimization
        storage_spend = category_spend.get(CostCategory.STORAGE.value, 0.0)
        if storage_spend > 50.0:
            savings = round(storage_spend * 0.30, 2)
            potential_savings += savings
            recommendations.append({
                "id": "REC_STORAGE_LIFECYCLE",
                "title": "Archive Cold Datasets to Glacier Tier",
                "description": "Historical uploaded datasets older than 90 days can be moved to cold storage.",
                "potential_savings_usd": savings,
                "urgency": "LOW",
            })

        # Fallback general recommendation if no specific threshold triggered
        if not recommendations:
            recommendations.append({
                "id": "REC_HEALTHY_SPEND",
                "title": "Infrastructure Spending Within Healthy Boundaries",
                "description": "All AI inference and infrastructure consumption is currently optimal.",
                "potential_savings_usd": 0.0,
                "urgency": "LOW",
            })

        return {
            "monthly_cost": round(total_cost, 2),
            "monthly_budget": self.monthly_budget_usd,
            "budget_utilized_percent": round((total_cost / self.monthly_budget_usd) * 100, 1) if self.monthly_budget_usd > 0 else 0.0,
            "category_spend": {k: round(v, 2) for k, v in category_spend.items()},
            "category_units": category_units,
            "optimization_savings": round(potential_savings, 2),
            "recommendations": recommendations,
        }

    def clear(self) -> None:
        self._records.clear()


cost_optimization_engine = CostOptimizationEngine()
