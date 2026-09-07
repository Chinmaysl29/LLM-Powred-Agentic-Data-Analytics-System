"""BM25 Sparse Retriever (Phase 5.6).

Inverted-index BM25 keyword retrieval for exact term matching.
"""

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from backend.app.schemas.vector_store import VectorSearchResult
from backend.rag.retrievers.base_retriever import BaseRetriever


class BM25Retriever(BaseRetriever):
    """BM25 Okapi sparse retriever built on an in-memory inverted index.

    BM25 score formula:
        score(D, Q) = Σ IDF(qi) * (f(qi,D) * (k1+1)) / (f(qi,D) + k1*(1-b+b*|D|/avgdl))
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._chunk_ids: List[str] = []
        self._document_ids: List[str] = []
        self._texts: List[str] = []
        self._metadatas: List[Dict[str, Any]] = []
        # term → list of (doc_index, term_freq)
        self._inverted_index: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        self._doc_lengths: List[int] = []
        self._avg_doc_length: float = 0.0
        self._corpus_size: int = 0

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r'\b[a-z0-9]+\b', text.lower())

    def index(
        self,
        chunk_ids: Any,
        document_ids: Optional[List[str]] = None,
        texts: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        if isinstance(chunk_ids, list) and chunk_ids and not isinstance(chunk_ids[0], str):
            chunks = chunk_ids
            c_ids = [getattr(c, "chunk_id", getattr(c, "id", str(i))) for i, c in enumerate(chunks)]
            d_ids = [getattr(c, "document_id", "") for c in chunks]
            txts = [getattr(c, "content", getattr(c, "text", "")) for c in chunks]
            metas = [getattr(c, "metadata", {}) or {} for c in chunks]
            return self.index(c_ids, d_ids, txts, metas)

        if document_ids is None:
            document_ids = ["" for _ in chunk_ids]
        if texts is None:
            texts = ["" for _ in chunk_ids]
        if metadatas is None:
            metadatas = [{} for _ in texts]

        for i, (cid, did, text, meta) in enumerate(zip(chunk_ids, document_ids, texts, metadatas)):

            doc_idx = len(self._chunk_ids)
            self._chunk_ids.append(cid)
            self._document_ids.append(did)
            self._texts.append(text)
            self._metadatas.append(meta)

            tokens = self._tokenize(text)
            self._doc_lengths.append(len(tokens))
            term_counts = Counter(tokens)

            for term, freq in term_counts.items():
                self._inverted_index[term].append((doc_idx, freq))

        self._corpus_size = len(self._chunk_ids)
        self._avg_doc_length = sum(self._doc_lengths) / max(1, self._corpus_size)

    def _idf(self, term: str) -> float:
        n_docs_with_term = len(self._inverted_index.get(term, []))
        if n_docs_with_term == 0:
            return 0.0
        return math.log((self._corpus_size - n_docs_with_term + 0.5) / (n_docs_with_term + 0.5) + 1.0)

    def _score_document(self, doc_idx: int, term_freq: int, idf: float) -> float:
        dl = self._doc_lengths[doc_idx]
        tf_norm = (term_freq * (self.k1 + 1)) / (
            term_freq + self.k1 * (1 - self.b + self.b * dl / max(1, self._avg_doc_length))
        )
        return idf * tf_norm

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        if self._corpus_size == 0:
            return []

        query_terms = self._tokenize(query)
        scores: Dict[int, float] = defaultdict(float)

        for term in set(query_terms):
            idf = self._idf(term)
            for doc_idx, freq in self._inverted_index.get(term, []):
                scores[doc_idx] += self._score_document(doc_idx, freq, idf)

        if not scores:
            return []

        max_score = max(scores.values()) or 1.0
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results: List[VectorSearchResult] = []
        for doc_idx, raw_score in ranked:
            norm_score = min(1.0, raw_score / max_score)
            if norm_score < min_score:
                continue

            meta = self._metadatas[doc_idx]
            if filters and not all(str(meta.get(k)) == str(v) for k, v in filters.items()):
                continue

            results.append(
                VectorSearchResult(
                    chunk_id=self._chunk_ids[doc_idx],
                    document_id=self._document_ids[doc_idx],
                    content=self._texts[doc_idx],
                    score=norm_score,
                    metadata=meta,
                )
            )
            if len(results) >= top_k:
                break

        return results

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        """Convenience search alias for retrieve."""
        return self.retrieve(query=query, top_k=top_k, min_score=min_score, filters=filters)

