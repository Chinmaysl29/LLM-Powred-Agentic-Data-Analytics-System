"""ChromaDB Persistent Vector Store (Phase 5.4)."""

import uuid
from typing import Any, Dict, List, Optional

from backend.app.schemas.vector_store import IndexStats, VectorSearchResult
from backend.rag.vectorstores.base_store import BaseVectorStore

try:
    import chromadb
    from chromadb.config import Settings
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False


class ChromaDBStore(BaseVectorStore):
    """ChromaDB persistent vector store with collection management."""

    def __init__(self, collection_name: str = "rag_chunks", persist_directory: Optional[str] = None) -> None:
        if not _CHROMA_AVAILABLE:
            raise RuntimeError("chromadb package is not installed.")

        self._collection_name = collection_name

        if persist_directory:
            self._client = chromadb.PersistentClient(path=persist_directory)
        else:
            self._client = chromadb.EphemeralClient()

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._dimension: int = 0

    def add(
        self,
        chunk_ids: List[str],
        document_ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        if not embeddings:
            return
        if metadatas is None:
            metadatas = [{} for _ in embeddings]

        if self._dimension == 0 and embeddings:
            self._dimension = len(embeddings[0])

        # ChromaDB metadatas must be flat str/int/float/bool dicts
        safe_metas = []
        for m, doc_id in zip(metadatas, document_ids):
            flat = {"document_id": doc_id}
            for k, v in (m or {}).items():
                if isinstance(v, (str, int, float, bool)):
                    flat[k] = v
                elif v is not None:
                    flat[k] = str(v)
            safe_metas.append(flat)

        self._collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=safe_metas,
        )

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        count = self._collection.count()
        if count == 0:
            return []

        where = None
        if filters:
            # Convert to ChromaDB where clause
            where = {k: {"$eq": v} for k, v in filters.items()} if len(filters) > 1 else filters

        n_results = min(top_k, count)
        try:
            result = self._collection.query(
                query_embeddings=[query_vector],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []

        results: List[VectorSearchResult] = []
        for chunk_id, doc, meta, dist in zip(
            result["ids"][0],
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            # ChromaDB cosine distance: score = 1 - distance
            score = max(0.0, min(1.0, 1.0 - float(dist)))
            if score < min_score:
                continue
            results.append(
                VectorSearchResult(
                    chunk_id=chunk_id,
                    document_id=meta.get("document_id", ""),
                    content=doc,
                    score=score,
                    metadata=meta,
                )
            )

        return results

    def delete(self, chunk_ids: List[str]) -> None:
        if chunk_ids:
            self._collection.delete(ids=chunk_ids)

    def clear(self) -> None:
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._dimension = 0

    def stats(self) -> IndexStats:
        count = self._collection.count()
        collections = [col.name for col in self._client.list_collections()]
        return IndexStats(
            total_vectors=count,
            dimension=self._dimension,
            index_type="chromadb_hnsw_cosine",
            collections=collections,
        )
