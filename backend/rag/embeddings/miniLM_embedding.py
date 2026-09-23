"""MiniLM / Fast Local Embedding Provider (Phase 5.3).

Generates 384-dimensional dense vectors with sentence-transformers or deterministic local fallback.
"""

import hashlib
import re
from typing import List
import numpy as np

from backend.rag.embeddings.base_embedding import BaseEmbedding


_MODEL_CACHE = {}


class MiniLMEmbedding(BaseEmbedding):
    """384-dimensional embedding provider using all-MiniLM-L6-v2 or deterministic projection."""

    DIMENSION = 384

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._st_model = None

        try:
            if model_name not in _MODEL_CACHE:
                from sentence_transformers import SentenceTransformer
                _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
            self._st_model = _MODEL_CACHE[model_name]
        except Exception:
            self._st_model = None

    @property
    def dimension(self) -> int:
        return self.DIMENSION

    @property
    def model_name(self) -> str:
        return self._model_name

    def _fallback_embed(self, text: str) -> List[float]:
        """Deterministic, normalized n-gram feature hashing projection to 384 dimensions."""
        if not text:
            return [0.0] * self.DIMENSION

        vec = np.zeros(self.DIMENSION, dtype=np.float32)
        cleaned = text.lower().strip()
        tokens = re.findall(r'\b\w+\b', cleaned)

        # Word-level features
        for token in tokens:
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self.DIMENSION
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vec[idx] += sign * 1.5

        # Character n-gram features (3-grams, 4-grams)
        for n in (3, 4):
            for i in range(len(cleaned) - n + 1):
                ngram = cleaned[i : i + n]
                h = int(hashlib.md5(ngram.encode("utf-8")).hexdigest()[:8], 16)
                idx = h % self.DIMENSION
                sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
                vec[idx] += sign * 0.5

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self._st_model is not None:
            try:
                embeddings = self._st_model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return embeddings.tolist()
            except Exception:
                pass
        return [self._fallback_embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        if self._st_model is not None:
            try:
                emb = self._st_model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
                return emb.tolist()
            except Exception:
                pass
        return self._fallback_embed(text)
