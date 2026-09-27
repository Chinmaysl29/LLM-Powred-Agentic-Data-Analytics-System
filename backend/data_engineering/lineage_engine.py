"""Data Governance & Lineage Engine (Phase 18.5.7).

Tracks complete end-to-end dataset evolution:
- Dataset Origin & Source Provenance
- Transformations (raw -> canonical -> cleaned -> features)
- Profile History & Quality Changes
- Downstream Forecasts & Visualizations
- Directed Acyclic Graph (DAG) generation (nodes & edges)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LineageNode:
    id: str
    label: str
    type: str  # "source", "canonical", "profile", "quality", "cleaned", "forecast", "visualization"
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageEdge:
    source: str
    target: str
    action: str  # "ingested", "standardized", "profiled", "assessed", "cleaned", "modeled", "visualized"
    timestamp: str


@dataclass
class TransformationEvent:
    event_id: str
    step_name: str
    transformation_type: str
    input_artifact: str
    output_artifact: str
    description: str
    operator: str
    parameters: dict[str, Any]
    timestamp: str


class DataLineageEngine:
    """Enterprise Data Governance and Provenance Tracking Engine."""

    def __init__(self, storage_dir: str | Path = "storage/lineage") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_lineage_file(self, dataset_id: str) -> Path:
        return self.storage_dir / f"{dataset_id}_lineage.json"

    def initialize_lineage(
        self,
        dataset_id: str,
        dataset_name: str,
        file_name: str,
        file_type: str,
        file_size_bytes: int,
        content_hash: str = "",
        author: str = "system",
    ) -> dict[str, Any]:
        """Create baseline lineage record for a newly ingested dataset."""
        now_iso = datetime.now(timezone.utc).isoformat()
        raw_node_id = f"{dataset_id}_raw"
        canonical_node_id = f"{dataset_id}_canonical"

        nodes = [
            LineageNode(
                id=raw_node_id,
                label=f"Raw: {file_name}",
                type="source",
                timestamp=now_iso,
                metadata={
                    "file_name": file_name,
                    "file_type": file_type,
                    "size_bytes": file_size_bytes,
                    "content_hash": content_hash,
                },
            ),
            LineageNode(
                id=canonical_node_id,
                label=f"Canonical JSON: {dataset_name}",
                type="canonical",
                timestamp=now_iso,
                metadata={"format": "canonical_json"},
            ),
        ]

        edges = [
            LineageEdge(
                source=raw_node_id,
                target=canonical_node_id,
                action="standardized",
                timestamp=now_iso,
            )
        ]

        record = {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "created_at": now_iso,
            "updated_at": now_iso,
            "origin": {
                "file_name": file_name,
                "file_type": file_type,
                "size_bytes": file_size_bytes,
                "content_hash": content_hash,
                "author": author,
            },
            "transformations": [
                {
                    "step_name": "initial_upload",
                    "action": "ingestion",
                    "timestamp": now_iso,
                    "description": f"Uploaded {file_name} to Enterprise Data Lake",
                }
            ],
            "profiles_history": [],
            "quality_history": [],
            "forecast_history": [],
            "graph": {
                "nodes": [asdict(n) for n in nodes],
                "edges": [asdict(e) for e in edges],
            },
        }

        self._save(dataset_id, record)
        return record

    def load_lineage(self, dataset_id: str) -> dict[str, Any]:
        """Load lineage document or generate stub if not yet persisted."""
        path = self._get_lineage_file(dataset_id)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Return default initialized structure if file not found
        return self.initialize_lineage(
            dataset_id=dataset_id,
            dataset_name=f"Dataset {dataset_id[:8]}",
            file_name="dataset.csv",
            file_type="csv",
            file_size_bytes=1024,
        )

    def _save(self, dataset_id: str, record: dict[str, Any]) -> None:
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        file_path = self._get_lineage_file(dataset_id)
        file_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    def record_transformation(
        self,
        dataset_id: str,
        step_name: str,
        transformation_type: str,
        description: str,
        operator: str = "system",
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an explicit data modification or cleaning event."""
        import uuid
        now_iso = datetime.now(timezone.utc).isoformat()
        lineage = self.load_lineage(dataset_id)

        clean_node_id = f"{dataset_id}_{step_name}_{uuid.uuid4().hex[:6]}"
        new_node = LineageNode(
            id=clean_node_id,
            label=f"Transform: {step_name}",
            type="cleaned",
            timestamp=now_iso,
            metadata={"transformation_type": transformation_type, "parameters": parameters or {}},
        )

        parent_node_id = lineage["graph"]["nodes"][-1]["id"]
        new_edge = LineageEdge(
            source=parent_node_id,
            target=clean_node_id,
            action="cleaned",
            timestamp=now_iso,
        )

        lineage["transformations"].append({
            "step_name": step_name,
            "transformation_type": transformation_type,
            "description": description,
            "operator": operator,
            "parameters": parameters or {},
            "timestamp": now_iso,
        })
        lineage["graph"]["nodes"].append(asdict(new_node))
        lineage["graph"]["edges"].append(asdict(new_edge))

        self._save(dataset_id, lineage)
        return lineage

    def record_profile_event(self, dataset_id: str, profile_summary: dict[str, Any]) -> dict[str, Any]:
        """Record profiling event and add node to lineage DAG."""
        now_iso = datetime.now(timezone.utc).isoformat()
        lineage = self.load_lineage(dataset_id)

        prof_node_id = f"{dataset_id}_profile_{len(lineage['profiles_history']) + 1}"
        new_node = LineageNode(
            id=prof_node_id,
            label="EDA Profile",
            type="profile",
            timestamp=now_iso,
            metadata={
                "duplicate_rows": profile_summary.get("duplicate_rows", 0),
                "numeric_columns_count": len(profile_summary.get("numeric_columns_profile", {})),
            },
        )

        canonical_id = f"{dataset_id}_canonical"
        new_edge = LineageEdge(
            source=canonical_id,
            target=prof_node_id,
            action="profiled",
            timestamp=now_iso,
        )

        lineage["profiles_history"].append({
            "timestamp": now_iso,
            "profile_summary": profile_summary,
        })
        lineage["graph"]["nodes"].append(asdict(new_node))
        lineage["graph"]["edges"].append(asdict(new_edge))

        self._save(dataset_id, lineage)
        return lineage

    def record_quality_event(self, dataset_id: str, quality_summary: dict[str, Any]) -> dict[str, Any]:
        """Record data quality evaluation and add node to lineage DAG."""
        now_iso = datetime.now(timezone.utc).isoformat()
        lineage = self.load_lineage(dataset_id)

        qual_node_id = f"{dataset_id}_quality_{len(lineage['quality_history']) + 1}"
        new_node = LineageNode(
            id=qual_node_id,
            label=f"Quality: {quality_summary.get('overall_score', 0):.1f}%",
            type="quality",
            timestamp=now_iso,
            metadata={
                "overall_score": quality_summary.get("overall_score"),
                "classification": quality_summary.get("quality_classification"),
            },
        )

        canonical_id = f"{dataset_id}_canonical"
        new_edge = LineageEdge(
            source=canonical_id,
            target=qual_node_id,
            action="assessed",
            timestamp=now_iso,
        )

        lineage["quality_history"].append({
            "timestamp": now_iso,
            "quality_summary": quality_summary,
        })
        lineage["graph"]["nodes"].append(asdict(new_node))
        lineage["graph"]["edges"].append(asdict(new_edge))

        self._save(dataset_id, lineage)
        return lineage

    def record_forecast_event(
        self,
        dataset_id: str,
        run_id: str,
        model_name: str,
        target: str,
        horizon: int,
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Record time-series forecast execution in lineage graph."""
        now_iso = datetime.now(timezone.utc).isoformat()
        lineage = self.load_lineage(dataset_id)

        fc_node_id = f"{dataset_id}_forecast_{run_id[:8]}"
        new_node = LineageNode(
            id=fc_node_id,
            label=f"Forecast: {model_name.upper()} ({target})",
            type="forecast",
            timestamp=now_iso,
            metadata={
                "run_id": run_id,
                "model": model_name,
                "target": target,
                "horizon": horizon,
                "metrics": metrics,
            },
        )

        canonical_id = f"{dataset_id}_canonical"
        new_edge = LineageEdge(
            source=canonical_id,
            target=fc_node_id,
            action="modeled",
            timestamp=now_iso,
        )

        lineage["forecast_history"].append({
            "run_id": run_id,
            "model": model_name,
            "target": target,
            "horizon": horizon,
            "metrics": metrics,
            "timestamp": now_iso,
        })
        lineage["graph"]["nodes"].append(asdict(new_node))
        lineage["graph"]["edges"].append(asdict(new_edge))

        self._save(dataset_id, lineage)
        return lineage

    def generate_lineage_graph(self, dataset_id: str) -> dict[str, Any]:
        """Generate structured DAG graph nodes and edges for visualization."""
        lineage = self.load_lineage(dataset_id)
        return {
            "dataset_id": dataset_id,
            "dataset_name": lineage.get("dataset_name"),
            "nodes": lineage.get("graph", {}).get("nodes", []),
            "edges": lineage.get("graph", {}).get("edges", []),
            "total_transformations": len(lineage.get("transformations", [])),
            "total_forecasts": len(lineage.get("forecast_history", [])),
        }


# Global singleton instance
lineage_engine = DataLineageEngine()


def get_lineage_engine() -> DataLineageEngine:
    return lineage_engine
