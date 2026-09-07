"""Table-Aware Chunker (Phase 5.2).

Preserves Markdown table structure and repeats table headers across table splits.
"""

import uuid
from typing import Any, Dict, List, Optional

from backend.app.schemas.chunking import Chunk
from backend.rag.chunking.base_chunker import BaseChunker
from backend.rag.chunking.recursive_chunker import RecursiveCharacterChunker


class TableAwareChunker(BaseChunker):
    """Chunker designed for tabular content, preserving headers and row coherence."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.text_chunker = RecursiveCharacterChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def _is_table_line(self, line: str) -> bool:
        s = line.strip()
        return s.startswith("|") and s.endswith("|") and s.count("|") >= 2

    def _split_into_blocks(self, text: str) -> List[tuple[str, bool]]:
        """Splits text into a list of (block_content, is_table)."""
        lines = text.split("\n")
        blocks: List[tuple[str, bool]] = []
        current_lines: List[str] = []
        current_is_table: Optional[bool] = None

        for line in lines:
            is_tbl = self._is_table_line(line)
            if current_is_table is None:
                current_is_table = is_tbl
                current_lines.append(line)
            elif is_tbl == current_is_table:
                current_lines.append(line)
            else:
                blocks.append(("\n".join(current_lines), current_is_table))
                current_lines = [line]
                current_is_table = is_tbl

        if current_lines:
            blocks.append(("\n".join(current_lines), bool(current_is_table)))

        return blocks

    def _chunk_table(self, table_text: str) -> List[str]:
        """Chunks a Markdown table preserving header and separator row."""
        lines = [line for line in table_text.split("\n") if line.strip()]
        if len(lines) <= 2:
            return [table_text]

        header = lines[0]
        separator = lines[1] if len(lines) > 1 and "---" in lines[1] else ""
        header_block = f"{header}\n{separator}".strip() if separator else header
        header_cost = len(header_block) + 1

        rows = lines[2:] if separator else lines[1:]
        chunks: List[str] = []
        current_rows: List[str] = []
        current_cost = header_cost

        for row in rows:
            row_cost = len(row) + 1
            if current_cost + row_cost <= self.chunk_size:
                current_rows.append(row)
                current_cost += row_cost
            else:
                if current_rows:
                    chunks.append(f"{header_block}\n" + "\n".join(current_rows))
                current_rows = [row]
                current_cost = header_cost + row_cost

        if current_rows:
            chunks.append(f"{header_block}\n" + "\n".join(current_rows))

        return chunks if chunks else [table_text]

    def split_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        if not text or not text.strip():
            return []

        doc_id = document_id or str(uuid.uuid4())
        blocks = self._split_into_blocks(text)
        raw_chunks: List[str] = []

        for block_content, is_table in blocks:
            if not block_content.strip():
                continue
            if is_table:
                if len(block_content) <= self.chunk_size:
                    raw_chunks.append(block_content.strip())
                else:
                    table_subchunks = self._chunk_table(block_content)
                    raw_chunks.extend(table_subchunks)
            else:
                subchunks = self.text_chunker._recursive_split(
                    block_content, self.text_chunker.separators
                )
                raw_chunks.extend(subchunks)

        result_chunks: List[Chunk] = []
        search_start = 0

        for idx, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if not chunk_text:
                continue

            found_pos = text.find(chunk_text[:40], search_start)
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
