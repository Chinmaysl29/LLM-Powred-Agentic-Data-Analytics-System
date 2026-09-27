"""Dataset Capacity Analyzer for Pre-Ingest Resource Estimation (Phase 18.5.2).

Inspects incoming files before full ingestion to detect:
- Total row count
- Column count
- Estimated in-memory RAM consumption
- Processing cost / complexity tier
- Actionable warnings for exceeding enterprise capacity thresholds
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CapacityLimits:
    max_recommended_rows: int = 1_000_000
    hard_limit_rows: int = 10_000_000
    max_recommended_cols: int = 250
    hard_limit_cols: int = 1_000
    max_in_memory_mb: float = 1_000.0  # 1 GB
    hard_limit_mb: float = 4_000.0  # 4 GB


@dataclass
class DatasetCapacityReport:
    file_path: str
    file_type: str
    file_size_bytes: int
    file_size_mb: float
    estimated_rows: int
    column_count: int
    column_names: list[str]
    estimated_memory_mb: float
    processing_cost: str  # "low", "medium", "high", "excessive"
    recommended_mode: str  # "in_memory", "chunked", "streaming"
    warnings: list[str] = field(default_factory=list)
    is_within_limits: bool = True
    estimated_processing_sec: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DatasetCapacityAnalyzer:
    """Analyzes dataset scale prior to ingestion to safeguard memory and system responsiveness."""

    def __init__(self, limits: CapacityLimits | None = None) -> None:
        self.limits = limits or CapacityLimits()

    def analyze(self, file_path: str | Path, file_type: str | None = None) -> DatasetCapacityReport:
        """Run rapid capacity inspection on a dataset file."""
        path_obj = Path(file_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found for capacity analysis: {file_path}")

        file_size_bytes = path_obj.stat().st_size
        file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
        norm_type = (file_type or path_obj.suffix).lower().lstrip(".")

        if norm_type in ("csv", "txt"):
            return self._analyze_csv(path_obj, norm_type, file_size_bytes, file_size_mb)
        elif norm_type in ("parquet", "pq"):
            return self._analyze_parquet(path_obj, norm_type, file_size_bytes, file_size_mb)
        elif norm_type in ("xlsx", "xls"):
            return self._analyze_excel(path_obj, norm_type, file_size_bytes, file_size_mb)
        elif norm_type == "json":
            return self._analyze_json(path_obj, norm_type, file_size_bytes, file_size_mb)
        else:
            return self._fallback_analysis(path_obj, norm_type, file_size_bytes, file_size_mb)

    def _analyze_csv(
        self, path: Path, file_type: str, file_size_bytes: int, file_size_mb: float
    ) -> DatasetCapacityReport:
        """Inspect CSV by sampling initial rows and counting line density."""
        # 1. Read first 200 rows to determine column structure & memory per row
        sample_df = pd.read_csv(path, nrows=200)
        col_count = len(sample_df.columns)
        col_names = list(sample_df.columns)

        # Estimate memory per row using deep memory footprint of sample
        sample_mem_bytes = sample_df.memory_usage(deep=True).sum()
        bytes_per_row = (sample_mem_bytes / max(len(sample_df), 1))

        # 2. Count lines efficiently without loading into memory
        line_count = 0
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                line_count += chunk.count(b"\n")

        # Exclude header line
        total_rows = max(line_count - 1, len(sample_df))

        # Projected DataFrame RAM usage
        estimated_mem_bytes = total_rows * bytes_per_row
        estimated_mem_mb = round(estimated_mem_bytes / (1024 * 1024), 2)

        return self._evaluate_metrics(
            path=str(path),
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            total_rows=total_rows,
            col_count=col_count,
            col_names=col_names,
            estimated_mem_mb=estimated_mem_mb,
        )

    def _analyze_parquet(
        self, path: Path, file_type: str, file_size_bytes: int, file_size_mb: float
    ) -> DatasetCapacityReport:
        """Inspect Parquet metadata without loading table."""
        try:
            import pyarrow.parquet as pq
            meta = pq.read_metadata(path)
            total_rows = meta.num_rows
            col_count = meta.num_columns
            col_names = [meta.schema.names[i] for i in range(col_count)]
            # Parquet compression ratio is typically 3x to 5x
            estimated_mem_mb = round(file_size_mb * 4.0, 2)
        except Exception:
            sample_df = pd.read_parquet(path)
            total_rows = len(sample_df)
            col_count = len(sample_df.columns)
            col_names = list(sample_df.columns)
            estimated_mem_mb = round(sample_df.memory_usage(deep=True).sum() / (1024 * 1024), 2)

        return self._evaluate_metrics(
            path=str(path),
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            total_rows=total_rows,
            col_count=col_count,
            col_names=col_names,
            estimated_mem_mb=estimated_mem_mb,
        )

    def _analyze_excel(
        self, path: Path, file_type: str, file_size_bytes: int, file_size_mb: float
    ) -> DatasetCapacityReport:
        sample_df = pd.read_excel(path, nrows=100)
        col_count = len(sample_df.columns)
        col_names = list(sample_df.columns)
        # Excel typically expands 4x in RAM
        estimated_mem_mb = round(file_size_mb * 4.5, 2)
        estimated_rows = int(max((file_size_bytes / max(col_count * 20, 1)), len(sample_df)))
        return self._evaluate_metrics(
            path=str(path),
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            total_rows=estimated_rows,
            col_count=col_count,
            col_names=col_names,
            estimated_mem_mb=estimated_mem_mb,
        )

    def _analyze_json(
        self, path: Path, file_type: str, file_size_bytes: int, file_size_mb: float
    ) -> DatasetCapacityReport:
        # JSON expands 2.5x to 4x in memory
        estimated_mem_mb = round(file_size_mb * 3.0, 2)
        return self._evaluate_metrics(
            path=str(path),
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            total_rows=int(file_size_bytes / 200),
            col_count=10,
            col_names=["json_payload"],
            estimated_mem_mb=estimated_mem_mb,
        )

    def _fallback_analysis(
        self, path: Path, file_type: str, file_size_bytes: int, file_size_mb: float
    ) -> DatasetCapacityReport:
        return self._evaluate_metrics(
            path=str(path),
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            total_rows=1000,
            col_count=1,
            col_names=["content"],
            estimated_mem_mb=file_size_mb * 2,
        )

    def _evaluate_metrics(
        self,
        path: str,
        file_type: str,
        file_size_bytes: int,
        file_size_mb: float,
        total_rows: int,
        col_count: int,
        col_names: list[str],
        estimated_mem_mb: float,
    ) -> DatasetCapacityReport:
        warnings: list[str] = []
        is_within_limits = True

        # Determine processing cost tier
        if total_rows > 5_000_000 or estimated_mem_mb > self.limits.hard_limit_mb:
            cost = "excessive"
            recommended_mode = "streaming"
        elif total_rows > self.limits.max_recommended_rows or estimated_mem_mb > self.limits.max_in_memory_mb:
            cost = "high"
            recommended_mode = "chunked"
        elif total_rows > 100_000 or estimated_mem_mb > 250.0:
            cost = "medium"
            recommended_mode = "chunked"
        else:
            cost = "low"
            recommended_mode = "in_memory"

        # Check warnings against limits
        if total_rows > self.limits.hard_limit_rows:
            warnings.append(
                f"Dataset row count ({total_rows:,}) exceeds enterprise maximum hard limit ({self.limits.hard_limit_rows:,})."
            )
            is_within_limits = False
        elif total_rows > self.limits.max_recommended_rows:
            warnings.append(
                f"Large dataset detected ({total_rows:,} rows). Chunked streaming processing is mandatory."
            )

        if col_count > self.limits.hard_limit_cols:
            warnings.append(
                f"Column count ({col_count}) exceeds hard limit ({self.limits.hard_limit_cols}). Wide table may degrade performance."
            )
            is_within_limits = False
        elif col_count > self.limits.max_recommended_cols:
            warnings.append(f"Wide schema detected ({col_count} columns). Consider column pruning.")

        if estimated_mem_mb > self.limits.hard_limit_mb:
            warnings.append(
                f"Estimated RAM footprint ({estimated_mem_mb:,.1f} MB) exceeds maximum safe allocation limit ({self.limits.hard_limit_mb:,.1f} MB)."
            )
            is_within_limits = False
        elif estimated_mem_mb > self.limits.max_in_memory_mb:
            warnings.append(
                f"Estimated RAM footprint ({estimated_mem_mb:,.1f} MB) exceeds standard in-memory threshold. Streaming reads activated."
            )

        # Estimate processing duration: ~100k rows/sec for streaming processing
        est_sec = round(max(total_rows / 100_000.0, 0.2), 2)

        return DatasetCapacityReport(
            file_path=path,
            file_type=file_type,
            file_size_bytes=file_size_bytes,
            file_size_mb=file_size_mb,
            estimated_rows=total_rows,
            column_count=col_count,
            column_names=col_names,
            estimated_memory_mb=estimated_mem_mb,
            processing_cost=cost,
            recommended_mode=recommended_mode,
            warnings=warnings,
            is_within_limits=is_within_limits,
            estimated_processing_sec=est_sec,
        )
