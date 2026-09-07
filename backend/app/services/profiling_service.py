"""Checklist proxy for DataProfilingService."""

from backend.app.services.data_profiling_service import (
    DataProfilingService,
    get_data_profiling_service,
)

ProfilingService = DataProfilingService
get_profiling_service = get_data_profiling_service

__all__ = [
    "DataProfilingService",
    "ProfilingService",
    "get_data_profiling_service",
    "get_profiling_service",
]
