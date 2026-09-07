"""Versioned registration for supported background-job handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from backend.jobs.manager import JobType

JobHandler = Callable[[dict[str, Any]], Any | Awaitable[Any]]


@dataclass(frozen=True)
class RegisteredJob:
    job_type: JobType
    handler: JobHandler
    version: str = "1"


class JobRegistry:
    """Single source of truth for job handlers and compatible versions."""

    def __init__(self) -> None:
        self._entries: dict[JobType, RegisteredJob] = {}

    def register(self, job_type: JobType, handler: JobHandler, version: str = "1") -> RegisteredJob:
        if not callable(handler):
            raise TypeError("Job handler must be callable")
        if not version or not version.strip():
            raise ValueError("Job version is required")
        entry = RegisteredJob(job_type=job_type, handler=handler, version=version)
        self._entries[job_type] = entry
        return entry

    def resolve(self, job_type: JobType, version: str | None = None) -> JobHandler:
        entry = self._entries.get(job_type)
        if entry is None:
            raise KeyError(f"No handler registered for {job_type.value}")
        if version is not None and entry.version != version:
            raise ValueError(f"Unsupported {job_type.value} job version: {version}")
        return entry.handler

    def validate(self, job_type: JobType, version: str | None = None) -> bool:
        try:
            self.resolve(job_type, version)
        except (KeyError, ValueError):
            return False
        return True
