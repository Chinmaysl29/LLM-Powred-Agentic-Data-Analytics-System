"""Data Engineering package for large dataset scalability and streaming operations."""

from backend.data_engineering.streaming_reader import StreamingCSVReader, StreamingAggregator
from backend.data_engineering.capacity_analyzer import DatasetCapacityAnalyzer, DatasetCapacityReport, CapacityLimits
from backend.data_engineering.benchmark_suite import DatasetBenchmarkSuite, BenchmarkReport

__all__ = [
    "StreamingCSVReader",
    "StreamingAggregator",
    "DatasetCapacityAnalyzer",
    "DatasetCapacityReport",
    "CapacityLimits",
    "DatasetBenchmarkSuite",
    "BenchmarkReport",
]
