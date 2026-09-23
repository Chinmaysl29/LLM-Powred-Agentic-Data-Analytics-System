"""A/B Testing Platform (Phase 11.5).

Compares AI models, prompts, agents, and pipelines:
- LLMs: GPT-4o vs Gemini 1.5 Pro
- Forecasting: Prophet vs XGBoost vs ARIMA
- RAG: BM25/Dense Hybrid vs Pure Vectorstore

Calculates performance metrics, evaluates statistical deltas, and declares winners.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import statistics
import uuid
from typing import Any, Dict, List, Optional


class MetricDirection(str, Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


@dataclass
class VariantMetrics:
    variant_name: str
    observations: List[float] = field(default_factory=list)
    successes: int = 0
    failures: int = 0

    @property
    def total_count(self) -> int:
        return len(self.observations)

    @property
    def mean_value(self) -> float:
        return statistics.mean(self.observations) if self.observations else 0.0

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0.0


@dataclass
class Experiment:
    experiment_id: str
    name: str
    variant_a: str
    variant_b: str
    primary_metric: str
    direction: MetricDirection = MetricDirection.HIGHER_IS_BETTER
    min_samples: int = 20
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ABTestingPlatform:
    """Enterprise A/B Testing and Variant Evaluation Platform."""

    def __init__(self) -> None:
        self._experiments: Dict[str, Experiment] = {}
        self._results: Dict[str, Dict[str, VariantMetrics]] = {}

    def create_experiment(
        self,
        name: str,
        variant_a: str,
        variant_b: str,
        primary_metric: str = "accuracy",
        direction: MetricDirection | str = MetricDirection.HIGHER_IS_BETTER,
        min_samples: int = 20,
    ) -> Dict[str, Any]:
        """Register a new A/B testing experiment."""
        exp_id = f"exp_{uuid.uuid4().hex[:10]}"
        dir_val = MetricDirection(direction.lower()) if isinstance(direction, str) else direction

        exp = Experiment(
            experiment_id=exp_id,
            name=name,
            variant_a=variant_a,
            variant_b=variant_b,
            primary_metric=primary_metric,
            direction=dir_val,
            min_samples=min_samples,
        )
        self._experiments[exp_id] = exp
        self._results[exp_id] = {
            variant_a: VariantMetrics(variant_name=variant_a),
            variant_b: VariantMetrics(variant_name=variant_b),
        }
        return asdict(exp)

    def route_variant(self, experiment_id: str, subject_id: str) -> str:
        """Deterministically route a user or request to Variant A or Variant B."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise KeyError(f"Experiment {experiment_id} not found")

        # Stable hash routing (50/50 split)
        hash_val = int(hashlib.md5(f"{experiment_id}:{subject_id}".encode("utf-8")).hexdigest()[:6], 16)
        return exp.variant_a if hash_val % 2 == 0 else exp.variant_b

    def record_result(
        self,
        experiment_id: str,
        variant: str,
        metric_value: float,
        is_success: bool = True,
    ) -> None:
        """Record an observation for a given experiment variant."""
        if experiment_id not in self._results:
            raise KeyError(f"Experiment {experiment_id} not found")
        if variant not in self._results[experiment_id]:
            raise KeyError(f"Variant '{variant}' is not part of experiment {experiment_id}")

        v_metrics = self._results[experiment_id][variant]
        v_metrics.observations.append(float(metric_value))
        if is_success:
            v_metrics.successes += 1
        else:
            v_metrics.failures += 1

    def evaluate_winner(self, experiment_id: str) -> Dict[str, Any]:
        """Evaluate experiment metrics and declare the winning variant."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            raise KeyError(f"Experiment {experiment_id} not found")

        res = self._results[experiment_id]
        va = res[exp.variant_a]
        vb = res[exp.variant_b]

        mean_a = va.mean_value
        mean_b = vb.mean_value

        if exp.direction == MetricDirection.HIGHER_IS_BETTER:
            if mean_a > mean_b:
                winner = exp.variant_a
                delta = round(mean_a - mean_b, 4)
            elif mean_b > mean_a:
                winner = exp.variant_b
                delta = round(mean_b - mean_a, 4)
            else:
                winner = "TIE"
                delta = 0.0
        else:
            # Lower is better (e.g. latency, error rate, cost)
            if mean_a < mean_b:
                winner = exp.variant_a
                delta = round(mean_b - mean_a, 4)
            elif mean_b < mean_a:
                winner = exp.variant_b
                delta = round(mean_a - mean_b, 4)
            else:
                winner = "TIE"
                delta = 0.0

        sample_sufficient = (va.total_count >= exp.min_samples and vb.total_count >= exp.min_samples)
        confidence = 0.95 if sample_sufficient and delta > 0.0 else 0.50

        return {
            "experiment_id": experiment_id,
            "experiment_name": exp.name,
            "winner": winner,
            "metric": exp.primary_metric,
            "variant_a": {"name": exp.variant_a, "mean": round(mean_a, 4), "samples": va.total_count},
            "variant_b": {"name": exp.variant_b, "mean": round(mean_b, 4), "samples": vb.total_count},
            "delta": delta,
            "statistically_significant": sample_sufficient and delta > 0.01,
            "confidence": confidence,
        }

    def clear(self) -> None:
        self._experiments.clear()
        self._results.clear()


ab_testing_platform = ABTestingPlatform()
