"""RAG Evaluation Framework (Phase 18.6.2).

Enterprise evaluation engine computing:
  - Precision@K, Recall@K
  - Mean Reciprocal Rank (MRR)
  - Normalized Discounted Cumulative Gain (NDCG)
  - Context Relevance Score
  - Answer Relevance Score
  - Groundedness Score

Stores evaluation history and supports benchmarking datasets.
"""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class RAGEvalResult:
    eval_id: str
    query: str
    retrieved_chunk_ids: list[str]
    relevant_chunk_ids: list[str]
    answer: str
    ground_truth: str
    k: int
    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    context_relevance: float = 0.0
    answer_relevance: float = 0.0
    groundedness_score: float = 0.0
    overall_score: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RAGBenchmark:
    benchmark_id: str
    query: str
    relevant_chunk_ids: list[str]
    ground_truth_answer: str
    category: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)


class RAGEvaluationFramework:
    """Enterprise RAG evaluation engine with metric persistence and benchmarking."""

    def __init__(self, storage_dir: str | Path = "storage/embeddings") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._history_path = self.storage_dir / "rag_eval_history.json"
        self._benchmarks_path = self.storage_dir / "rag_benchmarks.json"

    @staticmethod
    def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
        if not retrieved or k == 0:
            return 0.0
        top_k = retrieved[:k]
        hits = sum(1 for r in top_k if r in relevant)
        return round(hits / k, 4)

    @staticmethod
    def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
        if not relevant or k == 0:
            return 0.0
        top_k = retrieved[:k]
        hits = sum(1 for r in top_k if r in relevant)
        return round(hits / len(relevant), 4)

    @staticmethod
    def mean_reciprocal_rank(retrieved: list[str], relevant: list[str]) -> float:
        for rank, chunk_id in enumerate(retrieved, start=1):
            if chunk_id in relevant:
                return round(1.0 / rank, 4)
        return 0.0

    @staticmethod
    def ndcg_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
        if not retrieved or not relevant:
            return 0.0
        top_k = retrieved[:k]
        def dcg(ranked: list[str]) -> float:
            return sum(
                (1.0 / math.log2(i + 2))
                for i, cid in enumerate(ranked)
                if cid in relevant
            )
        ideal = [cid for cid in relevant if cid in set(top_k)][:k]
        ideal_dcg = dcg(ideal)
        actual_dcg = dcg(top_k)
        return round(actual_dcg / ideal_dcg, 4) if ideal_dcg > 0 else 0.0

    @staticmethod
    def context_relevance(retrieved_texts: list[str], query: str) -> float:
        if not retrieved_texts or not query:
            return 0.0
        query_terms = set(query.lower().split())
        hits = sum(1 for text in retrieved_texts if any(term in text.lower() for term in query_terms))
        return round(hits / len(retrieved_texts), 4)

    @staticmethod
    def answer_relevance(answer: str, query: str) -> float:
        if not answer or not query:
            return 0.0
        query_terms = set(q for q in query.lower().split() if len(q) > 3)
        if not query_terms:
            return 0.5
        hits = sum(1 for term in query_terms if term in answer.lower())
        return round(hits / len(query_terms), 4)

    @staticmethod
    def groundedness_score(answer: str, context_texts: list[str]) -> float:
        if not answer or not context_texts:
            return 0.0
        context_combined = " ".join(context_texts).lower()
        sentences = [s.strip() for s in answer.split(".") if len(s.strip()) > 10]
        if not sentences:
            return 0.0
        supported = sum(
            1 for sent in sentences
            if any(word in context_combined for word in sent.lower().split() if len(word) > 4)
        )
        return round(supported / len(sentences), 4)

    def evaluate(
        self,
        query: str,
        retrieved_chunk_ids: list[str],
        retrieved_texts: list[str],
        relevant_chunk_ids: list[str],
        answer: str,
        ground_truth: str = "",
        k: int = 5,
    ) -> RAGEvalResult:
        eval_id = str(uuid4())
        k_eff = min(k, len(retrieved_chunk_ids))
        precision = self.precision_at_k(retrieved_chunk_ids, relevant_chunk_ids, k_eff)
        recall = self.recall_at_k(retrieved_chunk_ids, relevant_chunk_ids, k_eff)
        mrr = self.mean_reciprocal_rank(retrieved_chunk_ids, relevant_chunk_ids)
        ndcg = self.ndcg_at_k(retrieved_chunk_ids, relevant_chunk_ids, k_eff)
        ctx_rel = self.context_relevance(retrieved_texts, query)
        ans_rel = self.answer_relevance(answer, query)
        grounded = self.groundedness_score(answer, retrieved_texts)
        overall = round(
            (precision * 0.15 + recall * 0.15 + mrr * 0.10 + ndcg * 0.10
             + ctx_rel * 0.20 + ans_rel * 0.15 + grounded * 0.15), 4
        )
        result = RAGEvalResult(
            eval_id=eval_id, query=query,
            retrieved_chunk_ids=retrieved_chunk_ids, relevant_chunk_ids=relevant_chunk_ids,
            answer=answer, ground_truth=ground_truth, k=k_eff,
            precision_at_k=precision, recall_at_k=recall, mrr=mrr, ndcg=ndcg,
            context_relevance=ctx_rel, answer_relevance=ans_rel,
            groundedness_score=grounded, overall_score=overall,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._persist_result(result)
        return result

    def _persist_result(self, result: RAGEvalResult) -> None:
        history = self.load_history()
        history.append(result.to_dict())
        self._history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

    def load_history(self) -> list[dict[str, Any]]:
        if not self._history_path.exists():
            return []
        try:
            return json.loads(self._history_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def health_summary(self) -> dict[str, Any]:
        history = self.load_history()
        if not history:
            return {"status": "no_evaluations", "total_evals": 0}
        def avg(lst: list) -> float:
            return round(sum(lst) / len(lst), 4) if lst else 0.0
        scores = [h.get("overall_score", 0) for h in history]
        return {
            "status": "healthy" if avg(scores) >= 0.5 else "needs_improvement",
            "total_evals": len(history),
            "avg_overall_score": avg(scores),
            "avg_precision_at_k": avg([h.get("precision_at_k", 0) for h in history]),
            "avg_recall_at_k": avg([h.get("recall_at_k", 0) for h in history]),
            "avg_groundedness": avg([h.get("groundedness_score", 0) for h in history]),
            "latest_eval": history[-1] if history else None,
        }

    def add_benchmark(self, benchmark: RAGBenchmark) -> None:
        benchmarks = self.load_benchmarks()
        benchmarks.append(asdict(benchmark))
        self._benchmarks_path.write_text(json.dumps(benchmarks, indent=2), encoding="utf-8")

    def load_benchmarks(self) -> list[dict[str, Any]]:
        if not self._benchmarks_path.exists():
            return []
        try:
            return json.loads(self._benchmarks_path.read_text(encoding="utf-8"))
        except Exception:
            return []


__all__ = ["RAGEvaluationFramework", "RAGEvalResult", "RAGBenchmark"]
