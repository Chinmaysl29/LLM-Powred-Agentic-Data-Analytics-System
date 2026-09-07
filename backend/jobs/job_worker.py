"""Cooperative worker engine for processing the shared job manager queue."""

from __future__ import annotations

import asyncio
import logging

from backend.jobs.manager import BackgroundJob, BackgroundJobManager, JobStatus

logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(self, manager: BackgroundJobManager, concurrency: int = 1) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        self.manager = manager
        self.concurrency = concurrency
        self._stopping = asyncio.Event()
        self.dead_letter: list[str] = []

    async def process_one(self) -> BackgroundJob | None:
        job = await self.manager.run_next()
        if job is not None and job.status == JobStatus.FAILED:
            self.dead_letter.append(job.job_id)
            logger.error("Job moved to dead letter queue job_id=%s", job.job_id)
        return job

    async def run_until_idle(self) -> int:
        processed = 0
        while not self._stopping.is_set():
            jobs = await asyncio.gather(*(self.process_one() for _ in range(self.concurrency)))
            count = sum(job is not None for job in jobs)
            processed += count
            if not count:
                break
        return processed

    async def shutdown(self) -> None:
        self._stopping.set()
