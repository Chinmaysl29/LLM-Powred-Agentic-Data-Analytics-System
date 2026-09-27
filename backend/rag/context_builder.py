"""Context Builder — Token-budgeted, deduplicated, cited context assembly (Phase 18.6.2)."""

import hashlib
from typing import List, Optional

try:
    import tiktoken
    _tokenizer = tiktoken.get_encoding("cl100k_base")
except Exception:
    _tokenizer = None

from backend.app.schemas.context_builder import BuiltContext, ContextSource
from backend.app.schemas.vector_store import VectorSearchResult


def _count_tokens(text: str) -> int:
    if not text:
        return 0
    if _tokenizer is not None:
        try:
            return len(_tokenizer.encode(text, disallowed_special=()))
        except Exception:
            pass
    return max(1, len(text) // 4)


def _fingerprint(text: str) -> str:
    """Deduplicate by content fingerprint (first 200 chars normalised)."""
    return hashlib.md5(text[:200].lower().strip().encode("utf-8")).hexdigest()


class ContextBuilder:
    """Assembles retrieved chunks into a coherent, cited, token-budgeted context block.

    Phase 18.6.2 upgrade:
    - full_content: complete chunk text for grounding validation
    - char_offset: document-level character position for lineage
    - citation_ref: structured citation string for reports
    - metadata: raw chunk metadata passthrough
    """

    DEFAULT_MAX_TOKENS = 3000

    def __init__(self, max_tokens: int = DEFAULT_MAX_TOKENS) -> None:
        self.max_tokens = max_tokens

    def build(
        self,
        results: List[VectorSearchResult],
        max_tokens: Optional[int] = None,
    ) -> BuiltContext:
        budget = max_tokens if max_tokens is not None else self.max_tokens

        seen_fingerprints: set = set()
        sources: List[ContextSource] = []
        sections: List[str] = []
        total_tokens = 0
        truncated = False
        cumulative_char_offset = 0

        for idx, result in enumerate(results):
            fp = _fingerprint(result.content)
            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)

            source_label = f"[Source {idx + 1}]"
            full_text = result.content.strip()
            section = f"{source_label}\n{full_text}"
            section_tokens = _count_tokens(section) + 2  # +2 for separator

            if total_tokens + section_tokens > budget:
                truncated = True
                break

            sections.append(section)
            total_tokens += section_tokens

            meta = result.metadata or {}
            filename = meta.get("filename")
            file_type = meta.get("file_type")
            page_num = meta.get("page_number")

            # Structured citation reference for reports
            citation_ref = (
                f"{filename or result.document_id}"
                + (f", p.{page_num}" if page_num else "")
                + f" (score={result.score:.3f})"
            )

            sources.append(
                ContextSource(
                    source_id=source_label,
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    filename=filename,
                    file_type=file_type,
                    score=result.score,
                    # UI display: first 120 chars
                    preview=full_text[:120].strip(),
                    # Grounding validation: complete chunk text
                    full_content=full_text,
                    # Document lineage
                    page_number=page_num,
                    char_offset=cumulative_char_offset,
                    # Citation tracking
                    citation_ref=citation_ref,
                    # Raw metadata passthrough
                    metadata=dict(meta),
                )
            )
            cumulative_char_offset += len(full_text) + 2  # +2 for \n\n

        formatted_text = "\n\n".join(sections)
        return BuiltContext(
            formatted_text=formatted_text,
            sources=sources,
            token_count=total_tokens,
            truncated=truncated,
            chunk_count=len(sections),
        )

    def format_citations(self, sources: List[ContextSource]) -> str:
        """Format a readable citations footer."""
        if not sources:
            return ""
        lines = ["**Sources:**"]
        for s in sources:
            ref = s.citation_ref or (s.filename or s.document_id)
            lines.append(f"- {s.source_id} {ref}")
        return "\n".join(lines)
