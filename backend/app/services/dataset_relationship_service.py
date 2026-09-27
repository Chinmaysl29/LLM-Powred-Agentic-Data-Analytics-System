"""Enterprise Dataset Relationship Engine for Phase 20.7.

Automatically discovers joins and data models across multiple datasets:
- Primary Key (PK) detection via uniqueness, non-null, and semantic identifier patterns
- Foreign Key (FK) detection via value overlap/containment and column naming similarity
- Relationship type classification (1:1, 1:N, N:M)
- Enterprise Schema Graph generation (nodes = datasets, edges = joins)
- Automated multi-table SQL JOIN generation
"""

from __future__ import annotations

import logging
import re
from typing import Any
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DatasetRelationshipEngine:
    """Enterprise engine inferring data models and joins across heterogeneous datasets."""

    @staticmethod
    def detect_candidate_pks(df: pd.DataFrame) -> list[dict[str, Any]]:
        """Identify potential primary key columns."""
        candidates = []
        n_rows = len(df)
        if n_rows == 0:
            return candidates

        for col in df.columns:
            non_null = df[col].notnull().sum()
            if non_null != n_rows:
                continue  # PK cannot have nulls

            n_unique = df[col].nunique()
            uniqueness_ratio = n_unique / n_rows

            is_name_match = bool(re.search(r"(^id$|_id$|id_|^sku$|^code$|^key$|^uuid$)", col.lower()))

            if uniqueness_ratio >= 0.99:
                score = 1.0 if is_name_match else 0.85
                candidates.append({
                    "column": col,
                    "uniqueness_ratio": round(uniqueness_ratio, 4),
                    "confidence": score,
                    "dtype": str(df[col].dtype),
                })
        # Sort by confidence descending
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return candidates

    def detect_relationships(
        self,
        datasets: dict[str, pd.DataFrame],
    ) -> list[dict[str, Any]]:
        """Analyze pairs of datasets to discover joins and relationships."""
        discovered_joins: list[dict[str, Any]] = []
        dataset_names = list(datasets.keys())

        # Detect PKs for each dataset
        pk_map: dict[str, list[str]] = {}
        for name, df in datasets.items():
            pks = [c["column"] for c in self.detect_candidate_pks(df)]
            pk_map[name] = pks

        # Compare pairwise
        for i in range(len(dataset_names)):
            for j in range(i + 1, len(dataset_names)):
                name_a, name_b = dataset_names[i], dataset_names[j]
                df_a, df_b = datasets[name_a], datasets[name_b]

                joins = self._find_joins_between(name_a, df_a, pk_map[name_a], name_b, df_b, pk_map[name_b])
                discovered_joins.extend(joins)

        return discovered_joins

    def _find_joins_between(
        self,
        name_a: str,
        df_a: pd.DataFrame,
        pks_a: list[str],
        name_b: str,
        df_b: pd.DataFrame,
        pks_b: list[str],
    ) -> list[dict[str, Any]]:
        """Check column pairs between two datasets for foreign key matches."""
        joins = []

        for col_a in df_a.columns:
            for col_b in df_b.columns:
                # 1. Name similarity check
                norm_a = re.sub(r"[^a-z0-9]", "", col_a.lower())
                norm_b = re.sub(r"[^a-z0-9]", "", col_b.lower())

                name_match = (
                    norm_a == norm_b
                    or norm_a in norm_b
                    or norm_b in norm_a
                    or (norm_a.endswith("id") and norm_b.endswith("id"))
                )
                if not name_match:
                    continue

                # 2. Value intersection check
                set_a = set(df_a[col_a].dropna().astype(str).unique())
                set_b = set(df_b[col_b].dropna().astype(str).unique())
                if not set_a or not set_b:
                    continue

                intersection = len(set_a & set_b)
                overlap_ratio_b = intersection / len(set_b)
                overlap_ratio_a = intersection / len(set_a)
                max_overlap = max(overlap_ratio_a, overlap_ratio_b)

                if max_overlap >= 0.50:  # Strong overlap
                    # Infer cardinality
                    is_pk_a = col_a in pks_a
                    is_pk_b = col_b in pks_b

                    if is_pk_a and is_pk_b:
                        cardinality = "1:1"
                    elif is_pk_a and not is_pk_b:
                        cardinality = "1:N"
                    elif not is_pk_a and is_pk_b:
                        cardinality = "N:1"
                    else:
                        cardinality = "N:M"

                    confidence = round(min(0.99, max_overlap * (1.1 if norm_a == norm_b else 0.9)), 2)

                    joins.append({
                        "source_dataset": name_a,
                        "source_column": col_a,
                        "target_dataset": name_b,
                        "target_column": col_b,
                        "relationship_type": cardinality,
                        "overlap_ratio": round(max_overlap, 3),
                        "confidence": confidence,
                        "recommended_join_type": "INNER JOIN" if max_overlap > 0.85 else "LEFT JOIN",
                    })

        # Keep highest confidence join per dataset pair
        joins.sort(key=lambda x: x["confidence"], reverse=True)
        return joins

    def generate_schema_graph(
        self,
        datasets: dict[str, pd.DataFrame],
    ) -> dict[str, Any]:
        """Generate an Enterprise Schema Graph of nodes and edges."""
        nodes = []
        for name, df in datasets.items():
            pks = [c["column"] for c in self.detect_candidate_pks(df)]
            nodes.append({
                "id": name,
                "label": name.replace(".csv", "").replace(".xlsx", "").replace("_", " ").title(),
                "row_count": len(df),
                "column_count": len(df.columns),
                "primary_keys": pks,
                "columns": [
                    {"name": c, "type": str(df[c].dtype), "is_pk": c in pks}
                    for c in df.columns
                ],
            })

        edges = self.detect_relationships(datasets)

        return {
            "nodes": nodes,
            "edges": edges,
            "total_datasets": len(nodes),
            "total_relationships": len(edges),
        }

    def generate_multi_table_sql(
        self,
        base_dataset: str,
        target_dataset: str,
        relationship: dict[str, Any],
        select_columns: list[str] | None = None,
    ) -> str:
        """Generate ANSI SQL multi-table join statement."""
        src_ds = relationship["source_dataset"]
        src_col = relationship["source_column"]
        tgt_ds = relationship["target_dataset"]
        tgt_col = relationship["target_column"]
        join_type = relationship.get("recommended_join_type", "INNER JOIN")

        src_tbl = re.sub(r"[^a-zA-Z0-9_]", "_", src_ds.split(".")[0])
        tgt_tbl = re.sub(r"[^a-zA-Z0-9_]", "_", tgt_ds.split(".")[0])

        cols = ", ".join(select_columns) if select_columns else f"{src_tbl}.*, {tgt_tbl}.*"

        return (
            f"SELECT {cols}\n"
            f"FROM {src_tbl}\n"
            f"{join_type} {tgt_tbl}\n"
            f"  ON {src_tbl}.{src_col} = {tgt_tbl}.{tgt_col}\n"
            f"LIMIT 100;"
        )

    def build_star_schema_join(
        self,
        datasets: dict[str, pd.DataFrame],
        fact_dataset: str | None = None,
    ) -> dict[str, Any]:
        """Automatically synthesize a multi-table star schema join across 3+ datasets."""
        graph = self.generate_schema_graph(datasets)
        edges = graph["edges"]
        dataset_names = list(datasets.keys())

        if len(dataset_names) < 2:
            raise ValueError("Need at least 2 datasets to build a multi-table join.")

        # Determine fact table (the one with the largest row count or highest foreign connections)
        if not fact_dataset:
            fact_candidate = max(datasets.items(), key=lambda item: len(item[1]))[0]
            fact_dataset = fact_candidate

        fact_table_name = re.sub(r"[^a-zA-Z0-9_]", "_", fact_dataset.split(".")[0]).lower()
        joins_built = []
        joined_tables = {fact_dataset}

        for edge in edges:
            src = edge["source_dataset"]
            tgt = edge["target_dataset"]
            src_col = edge["source_column"]
            tgt_col = edge["target_column"]
            join_type = edge.get("recommended_join_type", "INNER JOIN")

            if src == fact_dataset and tgt not in joined_tables:
                dim_table = re.sub(r"[^a-zA-Z0-9_]", "_", tgt.split(".")[0]).lower()
                joins_built.append({
                    "table": dim_table,
                    "dataset": tgt,
                    "join_type": join_type,
                    "on": f"{fact_table_name}.{src_col} = {dim_table}.{tgt_col}",
                })
                joined_tables.add(tgt)
            elif tgt == fact_dataset and src not in joined_tables:
                dim_table = re.sub(r"[^a-zA-Z0-9_]", "_", src.split(".")[0]).lower()
                joins_built.append({
                    "table": dim_table,
                    "dataset": src,
                    "join_type": join_type,
                    "on": f"{fact_table_name}.{tgt_col} = {dim_table}.{src_col}",
                })
                joined_tables.add(src)

        # Assemble full multi-table SQL query
        sql_cols = [f"{fact_table_name}.*"]
        for j in joins_built:
            sql_cols.append(f"{j['table']}.*")

        sql_lines = [f"SELECT {', '.join(sql_cols)}", f"FROM {fact_table_name}"]
        for j in joins_built:
            sql_lines.append(f"{j['join_type']} {j['table']}\n  ON {j['on']}")
        sql_lines.append("LIMIT 100;")

        full_sql = "\n".join(sql_lines)

        return {
            "fact_table": fact_table_name,
            "fact_dataset": fact_dataset,
            "dimension_tables": [j["table"] for j in joins_built],
            "joins_count": len(joins_built),
            "sql": full_sql,
            "schema_graph": graph,
        }



_relationship_engine = DatasetRelationshipEngine()


def get_dataset_relationship_engine() -> DatasetRelationshipEngine:
    return _relationship_engine
