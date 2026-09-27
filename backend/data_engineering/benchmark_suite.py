"""Dataset Scalability Benchmark Suite (Phase 18.5.2).

Measures streaming ingestion, memory usage, and throughput across:
- 100k rows
- 500k rows
- 1M rows
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backend.data_engineering.capacity_analyzer import DatasetCapacityAnalyzer
from backend.data_engineering.streaming_reader import StreamingCSVReader

logger = logging.getLogger(__name__)


@dataclass
class SingleBenchmarkResult:
    target_rows: int
    actual_rows: int
    file_size_mb: float
    generation_sec: float
    generation_rows_per_sec: float
    analysis_sec: float
    predicted_memory_mb: float
    streaming_processing_sec: float
    processing_rows_per_sec: float
    peak_memory_mb: float
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    timestamp: str
    benchmarks: list[SingleBenchmarkResult]
    total_duration_sec: float
    all_passed: bool
    summary_markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "benchmarks": [asdict(b) for b in self.benchmarks],
            "total_duration_sec": self.total_duration_sec,
            "all_passed": self.all_passed,
            "summary_markdown": self.summary_markdown,
        }


class DatasetBenchmarkSuite:
    """Automated benchmark executor for validating scalability up to 1M+ rows."""

    def __init__(self, work_dir: str | Path = "storage/benchmarks") -> None:
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.reader = StreamingCSVReader(chunk_size=50_000)
        self.analyzer = DatasetCapacityAnalyzer()

    def generate_synthetic_csv(self, file_path: Path, num_rows: int) -> float:
        """Fast vectorized generation of realistic business dataset in chunks."""
        t0 = time.perf_counter()
        batch_size = 50_000
        remaining = num_rows
        is_first = True

        categories = np.array(["Software", "Hardware", "Consulting", "Cloud", "Support"])
        regions = np.array(["North America", "EMEA", "APAC", "LATAM"])

        while remaining > 0:
            current_batch = min(remaining, batch_size)
            offset = num_rows - remaining

            df_chunk = pd.DataFrame({
                "order_id": np.arange(offset, offset + current_batch),
                "customer_id": np.random.randint(1000, 99999, size=current_batch),
                "revenue": np.round(np.random.exponential(scale=250.0, size=current_batch) + 10.0, 2),
                "cost": np.round(np.random.uniform(5.0, 150.0, size=current_batch), 2),
                "units": np.random.randint(1, 20, size=current_batch),
                "category": np.random.choice(categories, size=current_batch),
                "region": np.random.choice(regions, size=current_batch),
                "discount_pct": np.round(np.random.uniform(0.0, 0.35, size=current_batch), 2),
            })

            mode = "w" if is_first else "a"
            header = is_first
            df_chunk.to_csv(file_path, mode=mode, header=header, index=False)
            is_first = False
            remaining -= current_batch

        return time.perf_counter() - t0

    def run_benchmark(
        self,
        row_counts: list[int] | None = None,
        max_allowed_peak_mb: float = 350.0,
    ) -> BenchmarkReport:
        """Execute full benchmark suite against specified row counts."""
        targets = row_counts or [100_000, 500_000, 1_000_000]
        results: list[SingleBenchmarkResult] = []
        overall_t0 = time.perf_counter()

        for rows in targets:
            test_file = self.work_dir / f"benchmark_{rows}.csv"
            logger.info("Executing benchmark for %d rows...", rows)

            # 1. Measure data generation / write speed
            gen_sec = self.generate_synthetic_csv(test_file, rows)
            file_size_mb = round(test_file.stat().st_size / (1024 * 1024), 2)
            gen_rate = round(rows / max(gen_sec, 0.001), 1)

            # 2. Measure capacity analysis
            t_ana0 = time.perf_counter()
            cap_report = self.analyzer.analyze(test_file, file_type="csv")
            ana_sec = round(time.perf_counter() - t_ana0, 4)

            # 3. Measure memory consumption and streaming throughput
            tracemalloc.start()
            t_proc0 = time.perf_counter()

            aggregations = self.reader.compute_streaming_aggregations(test_file, chunk_size=50_000)

            proc_sec = round(time.perf_counter() - t_proc0, 3)
            current_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            peak_mem_mb = round(peak_mem / (1024 * 1024), 2)
            proc_rate = round(rows / max(proc_sec, 0.001), 1)

            # Clean up test file to preserve disk space
            try:
                test_file.unlink(missing_ok=True)
            except Exception:
                pass

            # Verification assertions:
            # Memory should remain bounded under max_allowed_peak_mb regardless of dataset size
            passed = (
                aggregations["total_rows"] == rows
                and peak_mem_mb <= max_allowed_peak_mb
                and proc_sec > 0
            )

            results.append(SingleBenchmarkResult(
                target_rows=rows,
                actual_rows=aggregations["total_rows"],
                file_size_mb=file_size_mb,
                generation_sec=round(gen_sec, 3),
                generation_rows_per_sec=gen_rate,
                analysis_sec=ana_sec,
                predicted_memory_mb=cap_report.estimated_memory_mb,
                streaming_processing_sec=proc_sec,
                processing_rows_per_sec=proc_rate,
                peak_memory_mb=peak_mem_mb,
                passed=passed,
                details={
                    "chunks_processed": aggregations.get("chunks_processed", 0),
                    "mean_revenue": aggregations.get("numeric_aggregations", {}).get("revenue", {}).get("mean"),
                    "cost_tier": cap_report.processing_cost,
                },
            ))

        total_sec = round(time.perf_counter() - overall_t0, 3)
        all_passed = all(r.passed for r in results)

        # Markdown summary report
        md_lines = [
            "# Large Dataset Scalability Benchmark Report (Phase 18.5.2)",
            f"**Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
            f"**Total Benchmark Runtime**: {total_sec:.2f}s",
            f"**Overall Status**: {'PASSED' if all_passed else 'FAILED'}\n",
            "| Rows | File Size | Gen Time | Gen Rate | Process Time | Process Rate | Peak RAM | Status |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in results:
            status = "PASS" if r.passed else "FAIL"
            md_lines.append(
                f"| {r.target_rows:,} | {r.file_size_mb:.1f} MB | {r.generation_sec:.2f}s | {r.generation_rows_per_sec:,.0f} r/s | {r.streaming_processing_sec:.2f}s | {r.processing_rows_per_sec:,.0f} r/s | {r.peak_memory_mb:.1f} MB | {status} |"
            )

        summary_md = "\n".join(md_lines)
        report = BenchmarkReport(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            benchmarks=results,
            total_duration_sec=total_sec,
            all_passed=all_passed,
            summary_markdown=summary_md,
        )

        # Save to storage/benchmarks/benchmark_report.json
        report_file = self.work_dir / "scalability_benchmark_report.json"
        report_file.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

        return report
