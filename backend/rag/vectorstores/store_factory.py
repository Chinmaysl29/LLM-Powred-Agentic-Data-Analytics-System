"""Vector Store Factory (Phase 5.4)."""

from enum import Enum
from typing import Optional
from backend.rag.vectorstores.base_store import BaseVectorStore
from backend.rag.vectorstores.in_memory_store import InMemoryVectorStore


class VectorStoreType(str, Enum):
    IN_MEMORY = "in_memory"
    FAISS = "faiss"
    CHROMADB = "chromadb"


class VectorStoreFactory:
    """Factory to create and configure vector store backends."""

    @classmethod
    def get_store(
        cls,
        store_type: str | VectorStoreType = VectorStoreType.IN_MEMORY,
        **kwargs,
    ) -> BaseVectorStore:
        t = store_type.value if isinstance(store_type, VectorStoreType) else str(store_type).lower()

        if t == VectorStoreType.IN_MEMORY.value:
            return InMemoryVectorStore()

        elif t == VectorStoreType.FAISS.value:
            from backend.rag.vectorstores.faiss_store import FaissStore
            return FaissStore(**kwargs)

        elif t == VectorStoreType.CHROMADB.value:
            from backend.rag.vectorstores.chromadb_store import ChromaDBStore
            return ChromaDBStore(**kwargs)

        else:
            valid = [e.value for e in VectorStoreType]
            raise ValueError(f"Unknown vector store type '{t}'. Valid types: {valid}")
