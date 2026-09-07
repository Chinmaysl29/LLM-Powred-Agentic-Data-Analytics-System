"""Recursive Character Chunker (Phase 5.2).

Splits text hierarchically using semantic boundaries (paragraphs, lines, sentences, words).
"""

import uuid
from typing import Any, Dict, List, Optional

from backend.app.schemas.chunking import Chunk
from backend.rag.chunking.base_chunker import BaseChunker


class RecursiveCharacterChunker(BaseChunker):
    """Hierarchical text splitter preserving semantic integrity across boundaries."""

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
    ) -> None:
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.separators = separators or self.DEFAULT_SEPARATORS

    def _split_text_with_separator(self, text: str, separator: str) -> List[str]:
        if separator:
            return text.split(separator)
        return list(text)

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        final_chunks: List[str] = []
        separator = separators[-1]
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        splits = self._split_text_with_separator(text, separator)
        good_splits: List[str] = []

        for s in splits:
            if not s:
                continue
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if new_separators:
                    other_splits = self._recursive_split(s, new_separators)
                    good_splits.extend(other_splits)
                else:
                    good_splits.append(s)

        # Merge splits up to chunk_size with overlap
        current_chunk: List[str] = []
        current_len = 0
        join_str = separator if separator != "" else ""

        for piece in good_splits:
            piece_len = len(piece) + (len(join_str) if current_chunk else 0)
            if current_len + piece_len <= self.chunk_size:
                current_chunk.append(piece)
                current_len += piece_len
            else:
                if current_chunk:
                    merged = join_str.join(current_chunk).strip()
                    if merged:
                        final_chunks.append(merged)
                    
                    # Compute overlap from end of current_chunk
                    overlap_chunk: List[str] = []
                    overlap_len = 0
                    for prev_piece in reversed(current_chunk):
                        added_len = len(prev_piece) + (len(join_str) if overlap_chunk else 0)
                        if overlap_len + added_len <= self.chunk_overlap:
                            overlap_chunk.insert(0, prev_piece)
                            overlap_len += added_len
                        else:
                            break
                    current_chunk = overlap_chunk
                    current_len = overlap_len

                current_chunk.append(piece)
                current_len += len(piece) + (len(join_str) if len(current_chunk) > 1 else 0)

        if current_chunk:
            merged = join_str.join(current_chunk).strip()
            if merged:
                final_chunks.append(merged)

        return final_chunks

    def split_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        if not text or not text.strip():
            return []

        doc_id = document_id or str(uuid.uuid4())
        raw_chunks = self._recursive_split(text, self.separators)

        result_chunks: List[Chunk] = []
        search_start = 0

        for idx, chunk_text in enumerate(raw_chunks):
            chunk_text_stripped = chunk_text.strip()
            if not chunk_text_stripped:
                continue

            # Locate offsets in original text
            found_pos = text.find(chunk_text_stripped, search_start)
            if found_pos != -1:
                start_char = found_pos
                end_char = found_pos + len(chunk_text_stripped)
                # Next search moves forward with overlap consideration
                search_start = max(0, end_char - self.chunk_overlap)
            else:
                start_char = search_start
                end_char = search_start + len(chunk_text_stripped)
                search_start = end_char

            chunk_obj = self.create_chunk(
                content=chunk_text_stripped,
                document_id=doc_id,
                chunk_index=idx,
                start_char=start_char,
                end_char=end_char,
                source_metadata=metadata,
            )
            result_chunks.append(chunk_obj)

        return result_chunks
