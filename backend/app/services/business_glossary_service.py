"""Phase 22.3 — Business Glossary Portal & Metric Dictionary Service.

Provides an authoritative semantic layer and unified business vocabulary:
- Canonical business terms and definitions
- Explicit mathematical metric calculation formulas
- Business synonyms and semantic aliases
- Data dictionary mapping terms to verified physical database columns
- Stewardship and approval workflows
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)

GLOSSARY_STORAGE_PATH = Path("storage/glossary")


class BusinessGlossaryService:
    """Enterprise business glossary and metric dictionary service."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self.storage_dir = Path(storage_dir) if storage_dir else GLOSSARY_STORAGE_PATH
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._terms: Dict[str, Dict[str, Any]] = {}
        self._load_glossary()
        self._seed_default_terms()

    def _load_glossary(self) -> None:
        try:
            for f in self.storage_dir.glob("*.json"):
                with open(f, "r", encoding="utf-8") as fp:
                    entry = json.load(fp)
                    if "id" in entry:
                        self._terms[entry["id"]] = entry
        except Exception as exc:
            logger.warning("Error loading glossary: %s", exc)

    def _persist_term(self, term_id: str) -> None:
        if term_id not in self._terms:
            return
        out_file = self.storage_dir / f"{term_id}.json"
        try:
            with open(out_file, "w", encoding="utf-8") as fp:
                json.dump(self._terms[term_id], fp, indent=2, default=str)
        except Exception as exc:
            logger.error("Failed persisting term %s: %s", term_id, exc)

    def _seed_default_terms(self) -> None:
        """Seed foundational enterprise business terms if glossary is empty."""
        if self._terms:
            return

        defaults = [
            {
                "id": "term-revenue",
                "term": "Gross Revenue",
                "definition": "Total monetary volume generated from completed product and service sales transactions prior to deductions.",
                "formula": "SUM(unit_price * quantity * (1 - discount))",
                "synonyms": ["Sales Volume", "Topline Revenue", "Gross Merchandise Value", "GMV"],
                "category": "Financial",
                "owner": "Finance Team",
                "status": "Approved",
                "physical_mappings": [
                    {"dataset": "sales_performance_2026.csv", "column": "total_revenue"},
                    {"dataset": "finance_pnl_2026.csv", "column": "revenue"},
                ],
            },
            {
                "id": "term-gross-margin",
                "term": "Gross Margin Percentage",
                "definition": "Proportion of revenue retained after subtracting the direct costs of goods sold (COGS).",
                "formula": "((Gross Revenue - COGS) / Gross Revenue) * 100",
                "synonyms": ["Gross Margin %", "Margin Rate", "Gross Profit Margin"],
                "category": "Profitability",
                "owner": "FP&A Lead",
                "status": "Approved",
                "physical_mappings": [
                    {"dataset": "sales_performance_2026.csv", "column": "net_profit"},
                ],
            },
            {
                "id": "term-cac",
                "term": "Customer Acquisition Cost (CAC)",
                "definition": "Total sales and marketing expenditure divided by total new customers acquired in the reporting period.",
                "formula": "Total Marketing Spend / Total New Customers",
                "synonyms": ["Acquisition Cost", "Blended CAC"],
                "category": "Marketing & Growth",
                "owner": "Growth Analytics Lead",
                "status": "Approved",
                "physical_mappings": [
                    {"dataset": "marketing_attribution_2026.csv", "column": "cac"},
                ],
            },
            {
                "id": "term-stockout-risk",
                "term": "Stockout Risk Rate",
                "definition": "Percentage of inventory items with days of supply below emergency safety reorder threshold.",
                "formula": "(COUNT(SKUs WHERE days_of_supply < safety_threshold) / Total SKUs) * 100",
                "synonyms": ["Inventory Depletion Risk", "Out of Stock Hazard"],
                "category": "Supply Chain & Ops",
                "owner": "Supply Chain Operations Lead",
                "status": "Approved",
                "physical_mappings": [
                    {"dataset": "supply_chain_operations_2026.csv", "column": "inventory_status"},
                ],
            },
        ]

        for d in defaults:
            d["created_at"] = datetime.now(timezone.utc).isoformat()
            d["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._terms[d["id"]] = d
            self._persist_term(d["id"])

    def create_term(
        self,
        term: str,
        definition: str,
        formula: str = "",
        synonyms: List[str] | None = None,
        category: str = "General",
        owner: str = "Analytics Governance",
        physical_mappings: List[Dict[str, str]] | None = None,
    ) -> Dict[str, Any]:
        """Create a new standardized enterprise glossary term."""
        term_id = f"term-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "id": term_id,
            "term": term,
            "definition": definition,
            "formula": formula,
            "synonyms": synonyms or [],
            "category": category,
            "owner": owner,
            "status": "Approved",
            "physical_mappings": physical_mappings or [],
            "created_at": now,
            "updated_at": now,
        }
        self._terms[term_id] = entry
        self._persist_term(term_id)
        return entry

    def list_terms(self, category: str | None = None) -> List[Dict[str, Any]]:
        """List all glossary terms with optional category filter."""
        terms = list(self._terms.values())
        if category:
            terms = [t for t in terms if t.get("category", "").lower() == category.lower()]
        terms.sort(key=lambda x: x.get("term", "").lower())
        return terms

    def search_glossary(self, query: str) -> List[Dict[str, Any]]:
        """Find terms matching name, definition, or synonyms."""
        q_clean = query.lower().strip()
        matched = []
        for t in self._terms.values():
            term_match = q_clean in t.get("term", "").lower()
            def_match = q_clean in t.get("definition", "").lower()
            syn_match = any(q_clean in s.lower() for s in t.get("synonyms", []))
            if term_match or def_match or syn_match:
                matched.append(t)
        return matched

    def resolve_term(self, query_phrase: str) -> Optional[Dict[str, Any]]:
        """Resolve a free-form phrase to its canonical business term and physical mappings."""
        q = query_phrase.lower().strip()
        for t in self._terms.values():
            if q == t["term"].lower():
                return t
            if any(q == s.lower() for s in t.get("synonyms", [])):
                return t
        return None


_glossary_service = BusinessGlossaryService()


def get_business_glossary_service() -> BusinessGlossaryService:
    return _glossary_service
