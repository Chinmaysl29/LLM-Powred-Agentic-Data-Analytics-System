"""Query Rewriter for contextual query disambiguation (Phase 5.9).

Rewrites ambiguous follow-up queries using conversation history context.
"""

import re
from typing import List, Optional

from backend.app.schemas.memory import Message, MessageRole


class QueryRewriter:
    """Rule-based and LLM-augmented query rewriter for multi-turn disambiguation."""

    # Pronouns and anaphoric references that signal follow-up queries
    FOLLOW_UP_SIGNALS = re.compile(
        r'\b(it|they|them|that|this|those|these|he|she|same|the result|the data|the above|the previous)\b',
        re.IGNORECASE,
    )
    RELATIVE_TIME = re.compile(
        r'\b(last month|last quarter|previous period|last year|that period|the same period)\b',
        re.IGNORECASE,
    )

    def is_followup(self, query: str) -> bool:
        """Detect if query is likely a follow-up requiring context."""
        q = query.strip()
        if len(q.split()) <= 4:
            return True
        if self.FOLLOW_UP_SIGNALS.search(q):
            return True
        if q.endswith("?") and not re.search(r'\bwhat|who|where|how|when|why\b', q, re.IGNORECASE):
            return True
        return False

    def rewrite(self, query: str, history: List[Message]) -> str:
        """Attempt to resolve follow-up references using conversation history."""
        if not self.is_followup(query) or not history:
            return query

        # Gather context from recent user and assistant messages
        context_parts: List[str] = []
        for msg in reversed(history[-6:]):  # look back up to 6 messages
            if msg.role in (MessageRole.USER, MessageRole.ASSISTANT):
                context_parts.insert(0, f"{msg.role.value}: {msg.content[:200]}")

        if not context_parts:
            return query

        context_summary = " | ".join(context_parts)

        # Simple rule: prepend context summary as a prefix hint
        rewritten = f"[Context: {context_summary}] {query}"
        return rewritten

    def extract_entities(self, query: str) -> List[str]:
        """Extract probable named entities (capitalized multi-word phrases) for BM25 boosting."""
        return re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', query)
