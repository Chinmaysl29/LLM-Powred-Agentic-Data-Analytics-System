"""Semantic Chunker (Phase 5.2).

Groups full semantic units (sentences/paragraphs) without breaking syntactic integrity.
"""

import re
import uuid
from typing import Any, Dict, List, Optional

from backend.app.schemas.chunking import Chunk
from backend.rag.chunking.base_chunker import BaseChunker


class SemanticChunker(BaseChunker):
    """Chunks text along sentence boundaries preserving semantic flow."""

    SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def _split_into_sentences(self, text: str) -> List[str]:
        # Split by paragraph first to preserve block structure
        paragraphs = text.split("\n\n")
        sentences: List[str] = []

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            p_sentences = self.SENTENCE_PATTERN.split(p)
            for s in p_sentences:
                s = s.strip()
                if s:
                    sentences.append(s)

        return sentences

    def split_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        if not text or not text.strip():
            return []

        doc_id = document_id or str(uuid.uuid4())
        sentences = self._split_into_sentences(text)
        if not sentences:
            return []

        raw_chunks: List[str] = []
        current_sentences: List[str] = []
        current_len = 0

        for sentence in sentences:
            sentence_len = len(sentence) + (1 if current_sentences else 0)
            if current_len + sentence_len <= self.chunk_size:
                current_sentences.append(sentence)
                current_len += sentence_len
            else:
                if current_sentences:
                    raw_chunks.append(" ".join(current_sentences))
                    # Retain sentence overlap
                    overlap_sentences: List[str] = []
                    overlap_len = 0
                    for prev_sent in reversed(current_sentences):
                        sent_cost = len(prev_sent) + (1 if overlap_sentences else 0)
                        if overlap_len + sent_cost <= self.chunk_overlap:
                            overlap_sentences.insert(0, prev_sent)
                            overlap_len += sent_cost
                        else:
                            break
                    current_sentences = overlap_sentences
                    current_len = overlap_len

                current_sentences.append(sentence)
                current_len += len(sentence) + (1 if len(current_sentences) > 1 else 0)

        if current_sentences:
            raw_chunks.append(" ".join(current_sentences))

        result_chunks: List[Chunk] = []
        search_start = 0

        for idx, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue

            found_pos = text.find(chunk_text[:50], search_start)
            if found_pos != -1:
                start_char = found_pos
                end_char = found_pos + len(chunk_text)
                search_start = max(0, end_char - self.chunk_overlap)
            else:
                start_char = search_start
                end_char = search_start + len(chunk_text)
                search_start = end_char

            result_chunks.append(
                self.create_chunk(
                    content=chunk_text,
                    document_id=doc_id,
                    chunk_index=idx,
                    start_char=start_char,
                    end_char=end_char,
                    source_metadata=metadata,
                )
            )

        return result_chunks
