"""Canonical dataset loader used by agents and analytics services."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from backend.app.models.dataset import Dataset


class DatasetLoader:
    def load_dataframe(self, dataset: Dataset) -> pd.DataFrame:
        if dataset.canonical_format == "parquet" and dataset.canonical_path:
            return pd.read_parquet(dataset.canonical_path)
        if dataset.json_path:
            payload = json.loads(open(dataset.json_path, encoding="utf-8").read())
            if "records" in payload:
                return pd.DataFrame(payload["records"])
        raise ValueError("Dataset has no tabular canonical artifact")

    def load_document(self, dataset: Dataset) -> dict[str, Any]:
        if dataset.canonical_format != "document_json" or not dataset.json_path:
            raise ValueError("Dataset is not a document dataset")
        return json.loads(open(dataset.json_path, encoding="utf-8").read())
