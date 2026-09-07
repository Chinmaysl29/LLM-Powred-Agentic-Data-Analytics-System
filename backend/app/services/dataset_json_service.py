"""Write canonical dataset artifacts without discarding the source file."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.app.services.dataset_parser_service import DatasetParserService, ParsedDataset
from backend.app.services.storage_service import StorageService


class DatasetJsonService:
    def __init__(self, storage: StorageService, parser: DatasetParserService | None = None) -> None:
        self.storage = storage
        self.parser = parser or DatasetParserService()

    def materialize(self, dataset_id: str, dataset_name: str, original_path: str, file_type: str) -> dict[str, Any]:
        parsed = self.parser.parse(original_path, file_type)
        root = self.storage.dataset_directory(dataset_id)
        artifacts = root / "artifacts"
        canonical = root / "canonical"
        artifacts.mkdir(parents=True, exist_ok=True)
        canonical.mkdir(parents=True, exist_ok=True)
        source_hash = hashlib.sha256(Path(original_path).read_bytes()).hexdigest()
        if parsed.dataframe is None:
            json_path = artifacts / "document.json"
            json_path.write_text(json.dumps(parsed.document, ensure_ascii=False, default=str), encoding="utf-8")
            return {"json_path": str(json_path), "canonical_path": None, "canonical_format": "document_json", "content_hash": source_hash, "row_count": None, "column_count": None}
        return self._write_tabular(dataset_id, dataset_name, parsed.dataframe, artifacts, canonical, source_hash)

    @staticmethod
    def _write_tabular(dataset_id: str, dataset_name: str, frame: pd.DataFrame, artifacts: Path, canonical: Path, source_hash: str) -> dict[str, Any]:
        json_path = artifacts / "data.json"
        payload = {"dataset_id": dataset_id, "dataset_name": dataset_name, "columns": frame.columns.tolist(), "records": json.loads(frame.to_json(orient="records", date_format="iso"))}
        json_path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
        parquet_path = canonical / "data.parquet"
        try:
            frame.to_parquet(parquet_path, index=False)
            canonical_path, canonical_format = str(parquet_path), "parquet"
        except (ImportError, ValueError):
            canonical_path, canonical_format = str(json_path), "json"
        return {"json_path": str(json_path), "canonical_path": canonical_path, "canonical_format": canonical_format, "content_hash": source_hash, "row_count": int(len(frame)), "column_count": int(len(frame.columns))}

    @staticmethod
    def write_artifact(path: str | Path, payload: Any) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        serializable = payload.model_dump() if hasattr(payload, "model_dump") else payload
        Path(path).write_text(json.dumps(serializable, default=str, ensure_ascii=False), encoding="utf-8")
