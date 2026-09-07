"""Context Builder — Token-budgeted, deduplicated, cited context assembly (Phase 5.7)."""

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
    """Assembles retrieved chunks into a coherent, cited, token-budgeted context block."""

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

        for idx, result in enumerate(results):
            fp = _fingerprint(result.content)
            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)

            source_label = f"[Source {idx + 1}]"
            section = f"{source_label}\n{result.content.strip()}"
            section_tokens = _count_tokens(section) + 2  # +2 for separator

            if total_tokens + section_tokens > budget:
                truncated = True
                break

            sections.append(section)
            total_tokens += section_tokens

            meta = result.metadata or {}
            sources.append(
                ContextSource(
                    source_id=source_label,
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    filename=meta.get("filename"),
                    file_type=meta.get("file_type"),
                    score=result.score,
                    preview=result.content[:120].strip(),
                )
            )

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
            name = s.filename or s.document_id
            lines.append(f"- {s.source_id} {name} (score: {s.score:.2f})")
        return "\n".join(lines)
