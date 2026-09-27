"""Dataset Lineage Intelligence Service (Phase 18.6.5).

Tracks the complete journey of every dataset:
  Upload -> Canonical JSON -> Profile -> Quality -> Cleaning
  -> Embedding -> Forecast -> Report

Generates lineage graphs, stores transformation history,
and exposes a lineage API.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Lifecycle stage names (ordered)
LINEAGE_STAGES = [
    "upload",
    "canonical_json",
    "profile",
    "quality",
    "cleaning",
    "embedding",
    "forecast",
    "report",
]


@dataclass
class LineageEvent:
    """A single transformation or lifecycle event in a dataset's history."""
    stage: str
    status: str  # "success" | "failed" | "skipped"
    timestamp: str
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class DatasetLineage:
    """Complete lineage record for one dataset."""
    dataset_id: str
    filename: str
    file_type: str
    created_at: str
    events: list[LineageEvent] = field(default_factory=list)
    current_stage: str = "upload"
    completed_stages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "created_at": self.created_at,
            "current_stage": self.current_stage,
            "completed_stages": self.completed_stages,
            "events": [asdict(e) for e in self.events],
        }

    def to_graph(self) -> dict[str, Any]:
        """Return a DAG-style lineage graph for visualization."""
        nodes = []
        edges = []
        for i, stage in enumerate(LINEAGE_STAGES):
            status = (
                "completed" if stage in self.completed_stages
                else "active" if stage == self.current_stage
                else "pending"
            )
            failed = any(e.stage == stage and e.status == "failed" for e in self.events)
            if failed:
                status = "failed"
            nodes.append({"id": stage, "label": stage.replace("_", " ").title(), "status": status})
            if i > 0:
                edges.append({"from": LINEAGE_STAGES[i - 1], "to": stage})
        return {
            "dataset_id": self.dataset_id,
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "total_stages": len(LINEAGE_STAGES),
                "completed": len(self.completed_stages),
                "current": self.current_stage,
            },
        }


class DatasetLineageService:
    """Service for tracking dataset lifecycle and generating lineage graphs."""

    def __init__(self, lineage_dir: str | Path = "storage/lineage") -> None:
        self.lineage_dir = Path(lineage_dir)
        self.lineage_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, dataset_id: str) -> Path:
        return self.lineage_dir / f"{dataset_id}.json"

    def create(self, dataset_id: str, filename: str, file_type: str) -> DatasetLineage:
        """Initialize a new lineage record on dataset upload."""
        lineage = DatasetLineage(
            dataset_id=dataset_id,
            filename=filename,
            file_type=file_type,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self._save(lineage)
        return lineage

    def record_event(
        self,
        dataset_id: str,
        stage: str,
        status: str = "success",
        duration_ms: float = 0.0,
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> DatasetLineage | None:
        """Record a lifecycle event for a dataset."""
        lineage = self.load(dataset_id)
        if lineage is None:
            logger.warning("Cannot record event — lineage not found for dataset_id=%s", dataset_id)
            return None

        event = LineageEvent(
            stage=stage,
            status=status,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            duration_ms=round(duration_ms, 2),
            details=details or {},
            error=error,
        )
        lineage.events.append(event)

        if status == "success" and stage not in lineage.completed_stages:
            lineage.completed_stages.append(stage)

        # Advance current_stage to next pending stage
        for s in LINEAGE_STAGES:
            if s not in lineage.completed_stages:
                lineage.current_stage = s
                break
        else:
            lineage.current_stage = "complete"

        self._save(lineage)
        return lineage

    def load(self, dataset_id: str) -> DatasetLineage | None:
        """Load lineage record from storage."""
        path = self._path(dataset_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            events = [LineageEvent(**e) for e in data.get("events", [])]
            return DatasetLineage(
                dataset_id=data["dataset_id"],
                filename=data.get("filename", ""),
                file_type=data.get("file_type", ""),
                created_at=data.get("created_at", ""),
                events=events,
                current_stage=data.get("current_stage", "upload"),
                completed_stages=data.get("completed_stages", []),
            )
        except Exception as exc:
            logger.error("Failed to load lineage for %s: %s", dataset_id, exc)
            return None

    def get_graph(self, dataset_id: str) -> dict[str, Any] | None:
        """Return the lineage graph for a dataset."""
        lineage = self.load(dataset_id)
        if lineage is None:
            return None
        return lineage.to_graph()

    def list_all(self) -> list[dict[str, Any]]:
        """List summary of all dataset lineages."""
        result = []
        for path in self.lineage_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                result.append({
                    "dataset_id": data.get("dataset_id"),
                    "filename": data.get("filename"),
                    "current_stage": data.get("current_stage"),
                    "completed_stages": data.get("completed_stages", []),
                    "created_at": data.get("created_at"),
                })
            except Exception:
                continue
        return result

    def _save(self, lineage: DatasetLineage) -> None:
        self._path(lineage.dataset_id).write_text(
            json.dumps(lineage.to_dict(), indent=2), encoding="utf-8"
        )


_service_singleton: DatasetLineageService | None = None


def get_lineage_service(lineage_dir: str | Path = "storage/lineage") -> DatasetLineageService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = DatasetLineageService(lineage_dir)
    return _service_singleton


__all__ = ["DatasetLineageService", "DatasetLineage", "LineageEvent", "LINEAGE_STAGES", "get_lineage_service"]
