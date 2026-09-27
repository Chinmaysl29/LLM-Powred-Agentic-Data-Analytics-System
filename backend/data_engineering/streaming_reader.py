"""Streaming Dataset Reader and Incremental Aggregations Engine (Phase 18.5.2).

Provides memory-safe chunked reading, numerical aggregation via Welford's algorithm,
and streaming statistics without loading multi-gigabyte files into RAM.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Callable, Generator, Iterator

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE: int = 50_000


class StreamingAggregator:
    """Computes exact streaming summary statistics incrementally across chunks."""

    def __init__(self) -> None:
        self.total_rows: int = 0
        self.numeric_stats: dict[str, dict[str, Any]] = {}
        self.categorical_counts: dict[str, dict[str, int]] = {}
        self.column_null_counts: dict[str, int] = {}

    def update_chunk(self, chunk: pd.DataFrame) -> None:
        """Incrementally update metrics using incoming chunk data."""
        chunk_len = len(chunk)
        if chunk_len == 0:
            return

        self.total_rows += chunk_len

        # 1. Null counts
        for col in chunk.columns:
            nulls = int(chunk[col].isna().sum())
            self.column_null_counts[col] = self.column_null_counts.get(col, 0) + nulls

        # 2. Numeric aggregations via numerically stable incremental combination
        numeric_cols = chunk.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            series = chunk[col].dropna()
            n_b = len(series)
            if n_b == 0:
                continue

            mean_b = float(series.mean())
            var_b = float(series.var(ddof=0)) if n_b > 1 else 0.0
            m2_b = var_b * n_b
            min_b = float(series.min())
            max_b = float(series.max())
            sum_b = float(series.sum())

            if col not in self.numeric_stats:
                self.numeric_stats[col] = {
                    "count": n_b,
                    "sum": sum_b,
                    "mean": mean_b,
                    "m2": m2_b,
                    "min": min_b,
                    "max": max_b,
                }
            else:
                curr = self.numeric_stats[col]
                n_a = curr["count"]
                mean_a = curr["mean"]
                m2_a = curr["m2"]

                new_count = n_a + n_b
                delta = mean_b - mean_a
                new_mean = mean_a + delta * (n_b / new_count)
                new_m2 = m2_a + m2_b + (delta ** 2) * (n_a * n_b / new_count)
                new_min = min(curr["min"], min_b)
                new_max = max(curr["max"], max_b)
                new_sum = curr["sum"] + sum_b

                curr["count"] = new_count
                curr["sum"] = new_sum
                curr["mean"] = new_mean
                curr["m2"] = new_m2
                curr["min"] = new_min
                curr["max"] = new_max

        # 3. Categorical top frequencies (capped at 50 per column)
        cat_cols = chunk.select_dtypes(include=["object", "category", "string"]).columns
        for col in cat_cols:
            if col not in self.categorical_counts:
                self.categorical_counts[col] = {}
            top_chunk = chunk[col].value_counts().head(50)
            for val, count in top_chunk.items():
                str_val = str(val)
                self.categorical_counts[col][str_val] = self.categorical_counts[col].get(str_val, 0) + int(count)

    def finalize(self) -> dict[str, Any]:
        """Produce finalized descriptive summary."""
        final_numeric: dict[str, dict[str, Any]] = {}
        for col, stat in self.numeric_stats.items():
            count = stat["count"]
            variance = (stat["m2"] / (count - 1)) if count > 1 else 0.0
            std_dev = math.sqrt(variance) if variance >= 0 else 0.0
            final_numeric[col] = {
                "count": count,
                "sum": round(stat["sum"], 4),
                "mean": round(stat["mean"], 4),
                "variance": round(variance, 4),
                "std_dev": round(std_dev, 4),
                "min": round(stat["min"], 4),
                "max": round(stat["max"], 4),
            }

        return {
            "total_rows": self.total_rows,
            "null_counts": self.column_null_counts,
            "numeric": final_numeric,
            "numeric_aggregations": final_numeric,
            "top_categories": {
                col: sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
                for col, counts in self.categorical_counts.items()
            },
        }


class StreamingCSVReader:
    """Memory-safe chunked dataset reader with streaming transformations."""

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        self.chunk_size = chunk_size

    def read_csv_chunks(
        self,
        file_path: str | Path,
        chunk_size: int | None = None,
        usecols: list[str] | None = None,
    ) -> Iterator[pd.DataFrame]:
        """Yield streaming chunks using pd.read_csv(..., chunksize=chunk_size)."""
        actual_chunk = chunk_size or self.chunk_size
        path_obj = Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")

        logger.debug("Streaming CSV chunks from %s with chunk_size=%d", path_obj.name, actual_chunk)
        reader = pd.read_csv(path_obj, chunksize=actual_chunk, usecols=usecols)
        for chunk in reader:
            yield chunk

    def read_chunks(
        self,
        file_path: str | Path,
        chunk_size: int | None = None,
        usecols: list[str] | None = None,
    ) -> Iterator[pd.DataFrame]:
        """Convenience alias for read_csv_chunks."""
        return self.read_csv_chunks(file_path, chunk_size=chunk_size, usecols=usecols)


    def compute_streaming_aggregations(
        self,
        file_path: str | Path,
        chunk_size: int | None = None,
        callback: Callable[[int, int], None] | None = None,
    ) -> dict[str, Any]:
        """Execute one-pass streaming aggregation across all chunks without full-file RAM allocation."""
        aggregator = StreamingAggregator()
        chunk_idx = 0
        total_rows_processed = 0

        for chunk in self.read_csv_chunks(file_path, chunk_size=chunk_size):
            aggregator.update_chunk(chunk)
            chunk_idx += 1
            total_rows_processed += len(chunk)
            if callback:
                callback(chunk_idx, total_rows_processed)

        result = aggregator.finalize()
        result["chunks_processed"] = chunk_idx
        return result

    def stream_transform_and_save(
        self,
        source_path: str | Path,
        target_path: str | Path,
        transform_fn: Callable[[pd.DataFrame], pd.DataFrame],
        chunk_size: int | None = None,
    ) -> int:
        """Stream chunks through a transformation function and write output incrementally."""
        target_p = Path(target_path)
        target_p.parent.mkdir(parents=True, exist_ok=True)

        rows_written = 0
        is_first = True

        for chunk in self.read_csv_chunks(source_path, chunk_size=chunk_size):
            transformed = transform_fn(chunk)
            mode = "w" if is_first else "a"
            header = is_first
            transformed.to_csv(target_p, mode=mode, header=header, index=False)
            rows_written += len(transformed)
            is_first = False

        return rows_written
