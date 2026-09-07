"""Fixed Size Chunker (Phase 5.2).

Splits text strictly by fixed character length with overlap.
"""

import uuid
from typing import Any, Dict, List, Optional

from backend.app.schemas.chunking import Chunk
from backend.rag.chunking.base_chunker import BaseChunker


class FixedSizeChunker(BaseChunker):
    """Chunker splitting strictly on fixed character boundaries with overlap."""

    def split_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        if not text or not text.strip():
            return []

        doc_id = document_id or str(uuid.uuid4())
        step = self.chunk_size - self.chunk_overlap
        chunks: List[Chunk] = []
        chunk_idx = 0

        for start in range(0, len(text), step):
            end = min(start + self.chunk_size, len(text))
            chunk_content = text[start:end].strip()
            if not chunk_content:
                continue

            chunks.append(
                self.create_chunk(
                    content=chunk_content,
                    document_id=doc_id,
                    chunk_index=chunk_idx,
                    start_char=start,
                    end_char=end,
                    source_metadata=metadata,
                )
            )
            chunk_idx += 1
            if end >= len(text):
                break

        return chunks
