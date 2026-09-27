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
        self.storage.processed_dir.mkdir(parents=True, exist_ok=True)

        source_bytes = Path(original_path).read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()

        if parsed.dataframe is None:
            doc_payload = parsed.document or {}
            doc_json = json.dumps(doc_payload, ensure_ascii=False, default=str, indent=2)

            # Store in storage lake domains
            self.storage.save_canonical(dataset_id, doc_payload)
            processed_json_path = self.storage.processed_dir / f"{dataset_id}.json"
            processed_json_path.write_text(doc_json, encoding="utf-8")

            # Store in dataset registry
            (root / "document.json").write_text(doc_json, encoding="utf-8")
            (artifacts / "document.json").write_text(doc_json, encoding="utf-8")

            page_count = len(doc_payload.get("pages", []))
            return {
                "json_path": str(processed_json_path),
                "canonical_path": str(processed_json_path),
                "canonical_format": "document_json",
                "content_hash": source_hash,
                "row_count": page_count,
                "column_count": 0,
            }

        frame = parsed.dataframe
        records = json.loads(frame.to_json(orient="records", date_format="iso"))
        canonical_json = json.dumps(records, ensure_ascii=False, default=str, indent=2)

        # 1. Store canonical and processed JSON in storage lake domains
        self.storage.save_canonical(dataset_id, records)
        processed_json_path = self.storage.processed_dir / f"{dataset_id}.json"
        processed_json_path.write_text(canonical_json, encoding="utf-8")

        # 2. Store in dataset directory: data.json and artifacts/data.json
        full_payload = {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "columns": frame.columns.tolist(),
            "records": records,
        }
        full_json = json.dumps(full_payload, ensure_ascii=False, default=str, indent=2)
        (root / "data.json").write_text(full_json, encoding="utf-8")
        (artifacts / "data.json").write_text(full_json, encoding="utf-8")

        # 3. Store parquet for columnar analytics
        parquet_path = canonical / "data.parquet"
        try:
            frame.to_parquet(parquet_path, index=False)
            canonical_path, canonical_format = str(parquet_path), "parquet"
        except (ImportError, ValueError, Exception):
            canonical_path, canonical_format = str(processed_json_path), "json"

        return {
            "json_path": str(processed_json_path),
            "canonical_path": canonical_path,
            "canonical_format": canonical_format,
            "content_hash": source_hash,
            "row_count": int(len(frame)),
            "column_count": int(len(frame.columns)),
        }

    @staticmethod
    def write_artifact(path: str | Path, payload: Any) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        serializable = payload.model_dump() if hasattr(payload, "model_dump") else payload
        Path(path).write_text(json.dumps(serializable, default=str, ensure_ascii=False), encoding="utf-8")
