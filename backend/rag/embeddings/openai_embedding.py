"""OpenAI Embedding Provider (Phase 5.3)."""

import hashlib
import os
import re
from typing import List, Optional
import numpy as np

from backend.rag.embeddings.base_embedding import BaseEmbedding


class OpenAIEmbedding(BaseEmbedding):
    """OpenAI vector embedding provider with offline fallback."""

    DEFAULT_MODEL = "text-embedding-3-small"
    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
    ) -> None:
        self._model_name = model_name
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._dim = self.DIMENSIONS.get(model_name, 1536)
        self._client = None

        if self._api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except Exception:
                self._client = None

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    def _offline_embed(self, text: str) -> List[float]:
        """Offline fallback producing normalized dimension-accurate vector."""
        if not text:
            return [0.0] * self._dim

        vec = np.zeros(self._dim, dtype=np.float32)
        tokens = re.findall(r'\b\w+\b', text.lower().strip())
        for token in tokens:
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % self._dim
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vec[idx] += sign

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if self._client is not None:
            try:
                response = self._client.embeddings.create(
                    input=texts,
                    model=self._model_name,
                )
                return [item.embedding for item in response.data]
            except Exception:
                pass

        return [self._offline_embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        if self._client is not None:
            try:
                response = self._client.embeddings.create(
                    input=[text],
                    model=self._model_name,
                )
                return response.data[0].embedding
            except Exception:
                pass

        return self._offline_embed(text)
