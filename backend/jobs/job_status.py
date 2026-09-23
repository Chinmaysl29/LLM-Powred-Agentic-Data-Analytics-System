"""Lifecycle transition rules shared by job producers and workers."""

from __future__ import annotations

from datetime import datetime

from backend.jobs.manager import BackgroundJob, JobStatus


ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.QUEUED, JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: {JobStatus.QUEUED},
    JobStatus.CANCELLED: set(),
}


def can_transition(current: JobStatus, target: JobStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def duration_seconds(job: BackgroundJob) -> float | None:
    if not job.started_at or not job.completed_at:
        return None
    return max(0.0, (datetime.fromisoformat(job.completed_at) - datetime.fromisoformat(job.started_at)).total_seconds())
