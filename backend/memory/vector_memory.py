"""Vector Memory Module for semantic past analysis recall."""

from typing import Any
import numpy as np

class VectorMemory:
    """Semantic vector memory for indexing and retrieving analytical knowledge."""
    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def add_entry(self, doc_id: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        self._entries.append({
            "doc_id": doc_id,
            "content": content,
            "metadata": metadata or {},
        })

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        # Keyword-augmented matching
        q_tokens = set(query.lower().split())
        scored = []
        for entry in self._entries:
            c_tokens = set(entry["content"].lower().split())
            overlap = len(q_tokens & c_tokens)
            score = overlap / max(1, len(q_tokens))
            scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]
