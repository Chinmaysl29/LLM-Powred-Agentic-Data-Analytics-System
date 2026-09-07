"""
Phase 15.3 — Enterprise Memory System
Multi-tier, persistent-in-memory memory spanning conversations, projects,
business context, decision history, vector concepts, and long-term institutional
knowledge. Used by every autonomous agent in Phase 15.
"""

from __future__ import annotations

import uuid
import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.autonomous.enterprise_memory")


# ---------------------------------------------------------------------------
# Memory Schemas
# ---------------------------------------------------------------------------

class MemoryTier(str, Enum):
    CONVERSATION = "conversation"   # per-session dialogue context
    PROJECT      = "project"        # per-project analytical context
    BUSINESS     = "business"       # company-wide facts and KPIs
    VECTOR       = "vector"         # semantic/embedding-keyed memory
    DECISION     = "decision"       # past decisions and outcomes
    LONG_TERM    = "long_term"      # multi-year institutional knowledge


class ImportanceLevel(str, Enum):
    CRITICAL = "critical"     # 5  – never evict
    HIGH     = "high"         # 4
    MEDIUM   = "medium"       # 3
    LOW      = "low"          # 2
    TRIVIAL  = "trivial"      # 1  – first to evict


_IMPORTANCE_SCORE: Dict[str, int] = {
    ImportanceLevel.CRITICAL: 5,
    ImportanceLevel.HIGH:     4,
    ImportanceLevel.MEDIUM:   3,
    ImportanceLevel.LOW:      2,
    ImportanceLevel.TRIVIAL:  1,
}


class MemoryEntry(BaseModel):
    entry_id:        str            = Field(default_factory=lambda: str(uuid.uuid4()))
    tier:            MemoryTier
    subject:         str
    content:         str
    tags:            List[str]      = Field(default_factory=list)
    importance:      ImportanceLevel = ImportanceLevel.MEDIUM
    importance_score: int           = 3
    source_agent:    Optional[str]  = None
    project_id:      Optional[str]  = None
    created_at:      str            = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_accessed_at: str           = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    access_count:    int            = 0
    ttl_hours:       Optional[int]  = None   # None = immortal


class MemoryRetrievalResult(BaseModel):
    entries:       List[MemoryEntry]
    total_matched: int
    tiers_searched: List[str]
    query:         str


class MemoryStats(BaseModel):
    total_entries:      int
    entries_by_tier:    Dict[str, int]
    entries_by_importance: Dict[str, int]
    oldest_entry_age_hours: float
    most_accessed_subject:  Optional[str]


# ---------------------------------------------------------------------------
# Enterprise Memory System
# ---------------------------------------------------------------------------

class EnterpriseMemorySystem:
    """
    Multi-tier memory store that gives every autonomous agent access to the
    full historical context of the business — from the last 60 seconds of
    conversation to multi-year strategic decisions.
    """

    def __init__(self, max_entries_per_tier: int = 10_000) -> None:
        self._store:      Dict[str, MemoryEntry] = {}   # entry_id → entry
        self._tier_idx:   Dict[str, List[str]]   = {t: [] for t in MemoryTier}
        self._tag_idx:    Dict[str, List[str]]   = {}   # tag → [entry_id]
        self._max_per_tier = max_entries_per_tier
        logger.info("EnterpriseMemorySystem initialised (max %d/tier).", max_entries_per_tier)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def store(self, entry: MemoryEntry) -> MemoryEntry:
        """Write a memory entry; enforces tier capacity via LRI eviction."""
        entry.importance_score = _IMPORTANCE_SCORE.get(entry.importance, 3)

        # Capacity guard
        tier_entries = self._tier_idx[entry.tier]
        if len(tier_entries) >= self._max_per_tier:
            self._evict_lowest(entry.tier)

        self._store[entry.entry_id] = entry
        self._tier_idx[entry.tier].append(entry.entry_id)

        for tag in entry.tags:
            self._tag_idx.setdefault(tag, []).append(entry.entry_id)

        logger.debug("Memory stored: [%s] %s", entry.tier, entry.subject)
        return entry

    def _evict_lowest(self, tier: MemoryTier) -> None:
        """Remove the lowest-importance, least-recently-accessed entry in tier."""
        candidates = [
            self._store[eid]
            for eid in self._tier_idx[tier]
            if eid in self._store
        ]
        if not candidates:
            return
        victim = min(candidates, key=lambda e: (e.importance_score, e.access_count))
        self._tier_idx[tier].remove(victim.entry_id)
        for tag in victim.tags:
            if victim.entry_id in self._tag_idx.get(tag, []):
                self._tag_idx[tag].remove(victim.entry_id)
        del self._store[victim.entry_id]
        logger.debug("Evicted memory: %s", victim.subject)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query:        str,
        tiers:        Optional[List[MemoryTier]] = None,
        tags:         Optional[List[str]]         = None,
        project_id:   Optional[str]               = None,
        top_k:        int                         = 20,
    ) -> MemoryRetrievalResult:
        """
        Keyword + tag search across tiers.  For each matched entry the
        access_count is incremented and last_accessed_at refreshed.
        """
        search_tiers = tiers or list(MemoryTier)
        candidates:  List[MemoryEntry] = []
        q_lower = query.lower()

        for eid, entry in self._store.items():
            if entry.tier not in search_tiers:
                continue
            if project_id and entry.project_id != project_id:
                continue
            if tags and not any(t in entry.tags for t in tags):
                continue
            if q_lower and (
                q_lower not in entry.subject.lower()
                and q_lower not in entry.content.lower()
            ):
                continue
            candidates.append(entry)

        # Rank by importance × recency (access_count as proxy)
        ranked = sorted(
            candidates,
            key=lambda e: (e.importance_score, e.access_count),
            reverse=True,
        )[:top_k]

        # Touch records
        now = datetime.now(timezone.utc).isoformat()
        for entry in ranked:
            entry.last_accessed_at = now
            entry.access_count    += 1

        return MemoryRetrievalResult(
            entries=ranked,
            total_matched=len(candidates),
            tiers_searched=[t.value for t in search_tiers],
            query=query,
        )

    def recall_decisions(self, topic: str) -> List[MemoryEntry]:
        """Retrieve all past decisions related to a topic."""
        result = self.retrieve(query=topic, tiers=[MemoryTier.DECISION], top_k=50)
        return result.entries

    def recall_project_context(self, project_id: str) -> List[MemoryEntry]:
        """Retrieve all memory entries for a given project."""
        result = self.retrieve(query="", project_id=project_id, top_k=100)
        return result.entries

    def get_business_memory(self) -> List[MemoryEntry]:
        """All business-tier entries sorted by importance."""
        result = self.retrieve(query="", tiers=[MemoryTier.BUSINESS], top_k=200)
        return result.entries

    def summarize_business_memory(self) -> Dict[str, Any]:
        """Generate a structured digest of long-term + business memory."""
        business_entries = self.get_business_memory()
        lt_result = self.retrieve(query="", tiers=[MemoryTier.LONG_TERM], top_k=50)

        subjects = [e.subject for e in business_entries[:10]]
        critical = [e for e in business_entries if e.importance == ImportanceLevel.CRITICAL]

        return {
            "business_memory_count": len(business_entries),
            "long_term_memory_count": len(lt_result.entries),
            "critical_entries": len(critical),
            "top_subjects": subjects,
            "digest": f"System holds {len(business_entries)} business facts and "
                      f"{len(lt_result.entries)} long-term institutional memories.",
        }

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def forget(self, min_importance: ImportanceLevel = ImportanceLevel.TRIVIAL) -> int:
        """
        TTL-based eviction: remove all non-critical entries whose TTL has
        expired AND whose importance is at or below the threshold.
        """
        now  = datetime.now(timezone.utc)
        purge_ids: List[str] = []
        min_score = _IMPORTANCE_SCORE[min_importance]

        for eid, entry in list(self._store.items()):
            if entry.importance_score > min_score:
                continue
            if entry.ttl_hours is None:
                continue
            created = datetime.fromisoformat(entry.created_at)
            if (now - created) > timedelta(hours=entry.ttl_hours):
                purge_ids.append(eid)

        for eid in purge_ids:
            entry = self._store.pop(eid)
            if eid in self._tier_idx.get(entry.tier, []):
                self._tier_idx[entry.tier].remove(eid)
            for tag in entry.tags:
                if eid in self._tag_idx.get(tag, []):
                    self._tag_idx[tag].remove(eid)

        logger.info("Forgot %d expired memory entries.", len(purge_ids))
        return len(purge_ids)

    def get_memory_stats(self) -> MemoryStats:
        entries_by_tier:       Dict[str, int] = {}
        entries_by_importance: Dict[str, int] = {}
        access_tally:          Dict[str, int] = {}
        oldest_ts = None

        for entry in self._store.values():
            entries_by_tier[entry.tier]             = entries_by_tier.get(entry.tier, 0) + 1
            entries_by_importance[entry.importance] = entries_by_importance.get(entry.importance, 0) + 1
            access_tally[entry.subject]             = access_tally.get(entry.subject, 0) + entry.access_count

            created = datetime.fromisoformat(entry.created_at)
            if oldest_ts is None or created < oldest_ts:
                oldest_ts = created

        age_hours = 0.0
        if oldest_ts:
            age_hours = round(
                (datetime.now(timezone.utc) - oldest_ts).total_seconds() / 3600, 2
            )

        most_accessed = max(access_tally, key=access_tally.get) if access_tally else None

        return MemoryStats(
            total_entries=len(self._store),
            entries_by_tier=entries_by_tier,
            entries_by_importance=entries_by_importance,
            oldest_entry_age_hours=age_hours,
            most_accessed_subject=most_accessed,
        )
