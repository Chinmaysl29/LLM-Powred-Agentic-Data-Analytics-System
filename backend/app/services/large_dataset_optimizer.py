"""Large Dataset Optimization Service (Phase 18.6.4).

Supports streaming reads, chunked processing, memory estimation,
and capacity analysis for datasets up to 5M+ rows.
"""
from __future__ import annotations

import gc
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

import pandas as pd

logger = logging.getLogger(__name__)

# Memory thresholds in bytes
_MB = 1024 * 1024
_GB = 1024 * _MB

# Row-count tier definitions
DATASET_TIERS = {
    "small":    (0,       100_000),
    "medium":   (100_001, 500_000),
    "large":    (500_001, 1_000_000),
    "xlarge":   (1_000_001, 5_000_000),
    "xxlarge":  (5_000_001, float("inf")),
}


@dataclass
class DatasetCapacityReport:
    row_count: int
    column_count: int
    estimated_memory_mb: float
    tier: str
    chunk_size_recommended: int
    streaming_required: bool
    health_score: float
    warnings: list[str]
    recommendations: list[str]


class LargeDatasetOptimizer:
    """Streaming, chunked processing, and memory estimation for large datasets."""

    # Chunk sizes by tier
    CHUNK_SIZES = {
        "small": 10_000,
        "medium": 25_000,
        "large": 50_000,
        "xlarge": 100_000,
        "xxlarge": 200_000,
    }

    @staticmethod
    def estimate_memory_mb(df: pd.DataFrame) -> float:
        """Estimate DataFrame memory usage in MB."""
        return round(df.memory_usage(deep=True).sum() / _MB, 2)

    @staticmethod
    def estimate_memory_from_shape(rows: int, cols: int, avg_bytes_per_cell: float = 8.0) -> float:
        """Estimate memory from row/column counts without loading the file."""
        return round((rows * cols * avg_bytes_per_cell) / _MB, 2)

    @staticmethod
    def classify_tier(row_count: int) -> str:
        for tier, (lo, hi) in DATASET_TIERS.items():
            if lo <= row_count <= hi:
                return tier
        return "xxlarge"

    def analyze_capacity(self, row_count: int, col_count: int, file_size_mb: float = 0.0) -> DatasetCapacityReport:
        """Analyze dataset capacity and generate health score + recommendations."""
        tier = self.classify_tier(row_count)
        est_mem = self.estimate_memory_from_shape(row_count, col_count)
        chunk_size = self.CHUNK_SIZES[tier]
        streaming = row_count > 100_000
        warnings: list[str] = []
        recs: list[str] = []

        # Memory warnings
        avail_mb = self._available_memory_mb()
        if est_mem > avail_mb * 0.7:
            warnings.append(f"Estimated memory {est_mem:.0f}MB exceeds 70% of available RAM ({avail_mb:.0f}MB)")
            recs.append("Enable streaming mode and process in chunks")
        if est_mem > 2048:
            warnings.append(f"Dataset estimated at {est_mem:.0f}MB — consider columnar formats (Parquet)")
            recs.append("Convert to Parquet for 3-10x compression and faster reads")

        # Row count warnings
        if row_count > 1_000_000:
            recs.append(f"Use chunk_size={chunk_size:,} for safe processing")
        if row_count > 5_000_000:
            warnings.append("Dataset exceeds 5M rows — distributed processing recommended")
            recs.append("Consider Dask, Spark, or BigQuery for datasets of this scale")

        # Health score: penalise large memory, reward manageable size
        health = max(0.0, min(1.0, 1.0 - (est_mem / max(1.0, avail_mb))))
        if not warnings:
            health = max(health, 0.75)

        return DatasetCapacityReport(
            row_count=row_count,
            column_count=col_count,
            estimated_memory_mb=est_mem,
            tier=tier,
            chunk_size_recommended=chunk_size,
            streaming_required=streaming,
            health_score=round(health, 4),
            warnings=warnings,
            recommendations=recs,
        )

    def stream_csv(self, file_path: str | Path, chunk_size: int = 50_000) -> Generator[pd.DataFrame, None, None]:
        """Yield DataFrame chunks from a large CSV file."""
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            yield chunk
            gc.collect()

    def stream_parquet(self, file_path: str | Path, batch_size: int = 50_000) -> Generator[pd.DataFrame, None, None]:
        """Yield batched rows from a Parquet file."""
        try:
            import pyarrow.parquet as pq
            pf = pq.ParquetFile(file_path)
            for batch in pf.iter_batches(batch_size=batch_size):
                yield batch.to_pandas()
                gc.collect()
        except ImportError:
            df = pd.read_parquet(file_path)
            for i in range(0, len(df), batch_size):
                yield df.iloc[i:i + batch_size].copy()
                gc.collect()

    def safe_load(self, file_path: str | Path, max_memory_mb: float = 2048.0) -> pd.DataFrame | None:
        """Load a file safely; return None and log warning if memory limit would be exceeded."""
        path = Path(file_path)
        file_size_mb = path.stat().st_size / _MB if path.exists() else 0.0
        est = file_size_mb * 3.5  # rough expansion factor CSV -> DataFrame
        if est > max_memory_mb:
            logger.warning(
                "File %s estimated at %.0fMB in memory, exceeds limit %.0fMB — use streaming",
                file_path, est, max_memory_mb,
            )
            return None
        return pd.read_csv(path) if path.suffix == ".csv" else None

    @staticmethod
    def _available_memory_mb() -> float:
        """Return available system memory in MB, or a safe default."""
        try:
            import psutil
            return psutil.virtual_memory().available / _MB
        except ImportError:
            return 4096.0


def get_large_dataset_optimizer() -> LargeDatasetOptimizer:
    return LargeDatasetOptimizer()


__all__ = ["LargeDatasetOptimizer", "DatasetCapacityReport", "get_large_dataset_optimizer"]
