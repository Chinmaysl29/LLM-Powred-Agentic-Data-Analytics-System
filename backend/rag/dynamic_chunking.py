"""Dynamic Document Chunking Service (Phase 18.6.2).

Auto-detects document category and applies optimal chunking strategy.

Rules:
  Financial Reports  -> chunk_size=600, overlap=100
  Research Papers    -> chunk_size=800, overlap=150
  Policies           -> chunk_size=400, overlap=80
  General Docs       -> chunk_size=500, overlap=100
  PDFs (default)     -> chunk_size=600, overlap=100
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Document category detection
# -----------------------------------------------------------------------

_FINANCIAL_KEYWORDS = frozenset([
    "revenue", "profit", "ebitda", "earnings", "fiscal", "quarterly",
    "annual report", "balance sheet", "cash flow", "net income", "dividend",
    "operating margin", "capex", "financial", "p&l",
])
_RESEARCH_KEYWORDS = frozenset([
    "abstract", "methodology", "hypothesis", "dataset", "experiment",
    "results", "conclusion", "literature review", "figure", "table",
    "arxiv", "doi", "peer-reviewed", "bibliography", "references",
])
_POLICY_KEYWORDS = frozenset([
    "policy", "procedure", "compliance", "regulation", "guideline",
    "shall", "must", "prohibited", "authorized", "clause", "section",
    "effective date", "version", "amendment", "enforcement",
])


@dataclass
class ChunkingConfig:
    """Optimal chunking configuration for a document type."""
    category: str
    chunk_size: int
    chunk_overlap: int
    strategy: str = "recursive"


class DynamicChunkingService:
    """Auto-detects document category and returns optimal chunking config."""

    _CONFIGS: dict[str, ChunkingConfig] = {
        "financial": ChunkingConfig("financial", 600, 100, "recursive"),
        "research": ChunkingConfig("research", 800, 150, "recursive"),
        "policy": ChunkingConfig("policy", 400, 80, "recursive"),
        "general": ChunkingConfig("general", 500, 100, "recursive"),
    }

    def detect_category(self, content: str, filename: str = "") -> str:
        """Detect document category from content and filename signals."""
        text_lower = content[:3000].lower()
        fname_lower = filename.lower()

        # Filename-based signals
        if any(kw in fname_lower for kw in ["annual", "report", "financial", "earnings", "revenue"]):
            return "financial"
        if any(kw in fname_lower for kw in ["policy", "procedure", "compliance", "guideline"]):
            return "policy"
        if any(kw in fname_lower for kw in ["paper", "research", "study", "arxiv", "journal"]):
            return "research"

        # Content-based scoring
        scores: dict[str, int] = {"financial": 0, "research": 0, "policy": 0}
        words = set(re.findall(r"\b\w+\b", text_lower))
        for word in words:
            if word in _FINANCIAL_KEYWORDS:
                scores["financial"] += 1
            if word in _RESEARCH_KEYWORDS:
                scores["research"] += 1
            if word in _POLICY_KEYWORDS:
                scores["policy"] += 1

        best = max(scores, key=lambda k: scores[k])
        if scores[best] >= 2:
            return best
        return "general"

    def get_config(self, content: str, filename: str = "", file_type: str = "") -> ChunkingConfig:
        """Return optimal ChunkingConfig for the given document."""
        # PDF default: treat as financial unless content says otherwise
        if file_type.lower() == "pdf" and not content[:500].strip():
            return self._CONFIGS["financial"]

        category = self.detect_category(content, filename)
        config = self._CONFIGS.get(category, self._CONFIGS["general"])
        logger.info(
            "Dynamic chunking: file=%s category=%s chunk_size=%d overlap=%d",
            filename, category, config.chunk_size, config.chunk_overlap,
        )
        return config

    def get_config_dict(self, content: str, filename: str = "", file_type: str = "") -> dict[str, Any]:
        cfg = self.get_config(content, filename, file_type)
        return {
            "category": cfg.category,
            "chunk_size": cfg.chunk_size,
            "chunk_overlap": cfg.chunk_overlap,
            "strategy": cfg.strategy,
        }


_service_singleton: DynamicChunkingService | None = None


def get_dynamic_chunking_service() -> DynamicChunkingService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = DynamicChunkingService()
    return _service_singleton


__all__ = ["DynamicChunkingService", "ChunkingConfig", "get_dynamic_chunking_service"]
