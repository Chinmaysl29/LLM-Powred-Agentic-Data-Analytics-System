"""Model Evaluation Framework (Phase 11.3).

Evaluates and benchmarks AI models and agents:
- SQL Agent
- RAG Agent
- Forecast Agent
- Recommendation Agent

Measures:
- Accuracy
- Latency (Average, p50, p95)
- Success Rate
- Failure Rate
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
import statistics
import time
from typing import Any, Callable, Dict, List, Optional


class EvaluatedAgent(str, Enum):
    SQL_AGENT = "sql_agent"
    RAG_AGENT = "rag_agent"
    FORECAST_AGENT = "forecast_agent"
    RECOMMENDATION_AGENT = "recommendation_agent"


@dataclass
class EvaluationSample:
    query: str
    expected: Any
    actual: Optional[Any] = None
    is_correct: bool = False
    latency_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class ModelEvaluationReport:
    model: str
    total_evaluations: int
    accuracy: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    success_rate: float
    failure_rate: float
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelEvaluationFramework:
    """Enterprise AI Model Evaluator and Benchmark Engine."""

    def __init__(self) -> None:
        self._history: Dict[str, List[ModelEvaluationReport]] = {
            agent.value: [] for agent in EvaluatedAgent
        }

    def evaluate_batch(
        self,
        model: EvaluatedAgent | str,
        test_cases: List[Dict[str, Any]],
        predict_fn: Optional[Callable[[str], Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate a batch of benchmark questions against expected answers or ground truths.
        
        test_cases format:
        [
            {"query": "Total revenue?", "expected": 5000, "actual": 5000, "latency_ms": 120.0},
            ...
        ]
        """
        model_key = model.value if isinstance(model, EvaluatedAgent) else str(model).lower()
        if not test_cases:
            report = ModelEvaluationReport(
                model=model_key,
                total_evaluations=0,
                accuracy=0.0,
                avg_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                success_rate=0.0,
                failure_rate=0.0,
            )
            return report.to_dict()

        correct_count = 0
        success_count = 0
        failure_count = 0
        latencies: List[float] = []

        for case in test_cases:
            query = case.get("query", "")
            expected = case.get("expected")
            actual = case.get("actual")
            latency = float(case.get("latency_ms", 0.0))
            error = case.get("error")

            if predict_fn and actual is None and not error:
                t0 = time.perf_counter()
                try:
                    actual = predict_fn(query)
                    latency = (time.perf_counter() - t0) * 1000.0
                except Exception as ex:
                    error = str(ex)
                    latency = (time.perf_counter() - t0) * 1000.0

            latencies.append(latency)

            if error:
                failure_count += 1
            else:
                success_count += 1
                # Accuracy comparison: strict or normalized equivalence
                if actual == expected:
                    correct_count += 1
                elif isinstance(actual, str) and isinstance(expected, str):
                    if actual.strip().lower() == expected.strip().lower():
                        correct_count += 1
                elif isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
                    if math.isclose(float(actual), float(expected), rel_tol=1e-3, abs_tol=1e-3):
                        correct_count += 1

        total = len(test_cases)
        accuracy = round(correct_count / total, 4) if total > 0 else 0.0
        success_rate = round(success_count / total, 4) if total > 0 else 0.0
        failure_rate = round(failure_count / total, 4) if total > 0 else 0.0

        sorted_latencies = sorted(latencies)
        avg_latency = round(statistics.mean(sorted_latencies), 2) if sorted_latencies else 0.0
        
        # p50 and p95 calculations
        if sorted_latencies:
            idx_50 = int(round(0.50 * (len(sorted_latencies) - 1)))
            idx_95 = int(round(0.95 * (len(sorted_latencies) - 1)))
            p50 = round(sorted_latencies[idx_50], 2)
            p95 = round(sorted_latencies[idx_95], 2)
        else:
            p50 = 0.0
            p95 = 0.0

        report = ModelEvaluationReport(
            model=model_key,
            total_evaluations=total,
            accuracy=accuracy,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            success_rate=success_rate,
            failure_rate=failure_rate,
        )

        if model_key not in self._history:
            self._history[model_key] = []
        self._history[model_key].append(report)

        return report.to_dict()

    def get_latest_report(self, model: EvaluatedAgent | str) -> Optional[Dict[str, Any]]:
        model_key = model.value if isinstance(model, EvaluatedAgent) else str(model).lower()
        hist = self._history.get(model_key, [])
        return hist[-1].to_dict() if hist else None

    def get_all_reports(self) -> Dict[str, Any]:
        return {
            k: [r.to_dict() for r in v] for k, v in self._history.items() if v
        }

    def clear(self) -> None:
        for k in self._history:
            self._history[k].clear()


model_evaluation_framework = ModelEvaluationFramework()
