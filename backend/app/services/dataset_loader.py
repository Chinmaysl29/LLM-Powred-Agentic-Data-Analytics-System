"""Canonical dataset loader used by agents and analytics services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from backend.app.models.dataset import Dataset


class DatasetLoader:
    def load_dataframe(self, dataset: Dataset) -> pd.DataFrame:
        if dataset.canonical_format == "parquet" and dataset.canonical_path and Path(dataset.canonical_path).exists():
            return pd.read_parquet(dataset.canonical_path)
        if dataset.json_path and Path(dataset.json_path).exists():
            payload = json.loads(Path(dataset.json_path).read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return pd.DataFrame(payload)
            if isinstance(payload, dict):
                if "records" in payload:
                    return pd.DataFrame(payload["records"])
                elif "data" in payload:
                    return pd.DataFrame(payload["data"])
        raise ValueError("Dataset has no tabular canonical artifact")

    def load_document(self, dataset: Dataset) -> dict[str, Any]:
        if dataset.canonical_format != "document_json" or not dataset.json_path:
            raise ValueError("Dataset is not a document dataset")
        return json.loads(open(dataset.json_path, encoding="utf-8").read())
