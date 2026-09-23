"""Phase 16.3 background job lifecycle tests."""

import asyncio

from backend.jobs.manager import BackgroundJobManager, JobStatus, JobType


def test_job_create_execute_and_track_completion():
    async def scenario():
        manager = BackgroundJobManager()
        manager.register(JobType.EDA, lambda payload: {"rows": payload["rows"], "insights": 3})
        job = await manager.create_job(JobType.EDA, "tenant-a", {"rows": 50})
        assert job.status == JobStatus.QUEUED
        complete = await manager.run_next()
        assert complete.status == JobStatus.COMPLETED
        assert complete.result["insights"] == 3
        assert (await manager.get_job(job.job_id)).status == JobStatus.COMPLETED
    asyncio.run(scenario())


def test_failed_job_is_requeued_then_marked_failed_at_retry_limit():
    async def scenario():
        manager = BackgroundJobManager()

        def failing_handler(_payload):
            raise RuntimeError("forecast source unavailable")

        manager.register(JobType.FORECAST, failing_handler)
        job = await manager.create_job(JobType.FORECAST, "tenant-a", max_attempts=2)
        first = await manager.run_next()
        assert first.status == JobStatus.QUEUED and first.attempts == 1
        final = await manager.run_next()
        assert final.status == JobStatus.FAILED and final.attempts == 2
        assert "unavailable" in final.error
    asyncio.run(scenario())


def test_manual_retry_only_allows_failed_jobs_with_remaining_attempts():
    async def scenario():
        manager = BackgroundJobManager()
        manager.register(JobType.REPORT, lambda _payload: (_ for _ in ()).throw(RuntimeError("render failed")))
        job = await manager.create_job(JobType.REPORT, "tenant-a", max_attempts=2)
        await manager.run_next()
        # First failure auto-requeues; force a terminal failure and then verify retry protection.
        await manager.run_next()
        assert (await manager.get_job(job.job_id)).status == JobStatus.FAILED
        try:
            await manager.retry(job.job_id)
        except ValueError as error:
            assert "limit" in str(error)
        else:
            raise AssertionError("Retry beyond max attempts must be rejected")
    asyncio.run(scenario())
