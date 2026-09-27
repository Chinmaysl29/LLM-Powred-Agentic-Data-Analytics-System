"""Enterprise Semantic Business Layer for Phase 20.8.

Translates technical database columns and physical schemas into business terminology:
- Business Glossary (human terms to canonical definitions)
- Column Synonyms Mapping (e.g. rev_amt, sales_amt, turnover -> Revenue)
- Calculated Metric Definitions (e.g. Gross Profit = Revenue - COGS)
- Query Resolution for Text-to-SQL enrichment
"""

from __future__ import annotations

import logging
import re
from typing import Any
import pandas as pd

logger = logging.getLogger(__name__)


DEFAULT_GLOSSARY: dict[str, dict[str, Any]] = {
    "revenue": {
        "business_name": "Gross Revenue",
        "description": "Total monetary value realized from commercial sales before returns or deductions.",
        "synonyms": ["rev", "rev_amt", "sales", "sales_amt", "turnover", "gross_sales", "inflow", "total_amount"],
        "default_aggregation": "SUM",
        "format": "$#,##0.00",
        "category": "Financial",
    },
    "customer_id": {
        "business_name": "Customer Identifier",
        "description": "Unique enterprise key representing an individual or corporate purchasing entity.",
        "synonyms": ["cust_id", "client_id", "account_id", "user_id", "customer_num", "cid"],
        "default_aggregation": "COUNT_DISTINCT",
        "format": "string",
        "category": "Entity",
    },
    "quantity": {
        "business_name": "Order Quantity",
        "description": "Physical units or volume of items purchased per line item.",
        "synonyms": ["qty", "qty_sold", "units", "unit_count", "item_qty", "volume"],
        "default_aggregation": "SUM",
        "format": "#,##0",
        "category": "Operational",
    },
    "cogs": {
        "business_name": "Cost of Goods Sold",
        "description": "Direct costs attributable to the production or acquisition of the goods sold.",
        "synonyms": ["cost", "unit_cost", "direct_cost", "expense", "cogs_amt"],
        "default_aggregation": "SUM",
        "format": "$#,##0.00",
        "category": "Financial",
    },
    "profit": {
        "business_name": "Net Operating Profit",
        "description": "Earnings remaining after subtracting cost of goods sold from gross revenue.",
        "synonyms": ["net_profit", "gross_profit", "margin_amt", "earnings", "net_margin_amt"],
        "default_aggregation": "SUM",
        "format": "$#,##0.00",
        "calculation": "revenue - cogs",
        "category": "Financial",
    },
    "order_date": {
        "business_name": "Transaction Timestamp",
        "description": "Recorded date and time at which the commercial transaction occurred.",
        "synonyms": ["tx_date", "tx_ts", "date", "created_at", "trans_date", "purchase_date", "timestamp"],
        "default_aggregation": "COUNT",
        "format": "YYYY-MM-DD",
        "category": "Temporal",
    },
}


class SemanticBusinessLayer:
    """Service providing business glossary, synonym normalization, and SQL translation."""

    def __init__(self) -> None:
        self.glossary = {k: dict(v) for k, v in DEFAULT_GLOSSARY.items()}

    def add_term(
        self,
        canonical_key: str,
        business_name: str,
        description: str,
        synonyms: list[str],
        default_aggregation: str = "SUM",
        calculation: str | None = None,
    ) -> dict[str, Any]:
        """Register a new business concept into the semantic layer."""
        clean_key = canonical_key.lower().strip()
        term_def = {
            "business_name": business_name,
            "description": description,
            "synonyms": [s.lower().strip() for s in synonyms],
            "default_aggregation": default_aggregation,
            "format": "$#,##0.00",
            "calculation": calculation,
            "category": "Custom",
        }
        self.glossary[clean_key] = term_def
        return term_def

    def resolve_column_to_concept(self, column_name: str) -> dict[str, Any] | None:
        """Resolve a physical database column name to its canonical business concept."""
        col_norm = re.sub(r"[^a-z0-9]", "_", column_name.lower()).strip("_")

        # 1. Exact match on canonical key
        if col_norm in self.glossary:
            return {"canonical_key": col_norm, **self.glossary[col_norm]}

        # 2. Match on registered synonyms
        for key, defn in self.glossary.items():
            if col_norm in defn.get("synonyms", []):
                return {"canonical_key": key, **defn}

        # 3. Partial substring match
        for key, defn in self.glossary.items():
            for syn in defn.get("synonyms", []):
                if syn == col_norm or syn in col_norm or col_norm in syn:
                    return {"canonical_key": key, **defn}

        return None

    def map_dataset_schema(self, df: pd.DataFrame) -> dict[str, Any]:
        """Generate a complete semantic mapping dictionary for a given DataFrame schema."""
        mappings: dict[str, Any] = {}
        for col in df.columns:
            concept = self.resolve_column_to_concept(col)
            if concept:
                mappings[col] = {
                    "business_name": concept["business_name"],
                    "canonical_key": concept["canonical_key"],
                    "default_aggregation": concept["default_aggregation"],
                    "description": concept["description"],
                }
            else:
                # Default heuristic
                mappings[col] = {
                    "business_name": col.replace("_", " ").title(),
                    "canonical_key": col.lower(),
                    "default_aggregation": "SUM" if pd.api.types.is_numeric_dtype(df[col]) else "COUNT",
                    "description": f"Column {col}",
                }
        return mappings

    def translate_query_terms_to_columns(
        self,
        user_query: str,
        available_columns: list[str],
    ) -> dict[str, str]:
        """Translate natural language business terms in a user question into physical columns."""
        lower_q = user_query.lower()
        col_map: dict[str, str] = {}

        # Build reverse index from synonyms to physical columns
        for col in available_columns:
            concept = self.resolve_column_to_concept(col)
            if concept:
                key = concept["canonical_key"]
                synonyms = [key, concept["business_name"].lower()] + concept.get("synonyms", [])
                for syn in synonyms:
                    if syn in lower_q:
                        col_map[syn] = col

        return col_map


_semantic_layer = SemanticBusinessLayer()


def get_semantic_business_layer() -> SemanticBusinessLayer:
    return _semantic_layer
