"""Additional Phase 16.3 tests for lifecycle components beyond the smoke flow."""

import asyncio

from backend.jobs import BackgroundJobManager, JobRegistry, JobStatus, JobType, JobWorker


def test_cancel_progress_list_and_worker_dead_letter():
    async def scenario():
        manager = BackgroundJobManager()
        manager.register(JobType.EDA, lambda _payload: {"ok": True})
        job = await manager.create_job(JobType.EDA, "tenant-a", priority=9)
        assert (await manager.update_progress(job.job_id, 40)).progress == 40
        assert len(await manager.list_jobs("tenant-a", JobStatus.QUEUED)) == 1
        assert (await manager.cancel_job(job.job_id)).status == JobStatus.CANCELLED

        manager.register(JobType.REPORT, lambda _payload: (_ for _ in ()).throw(RuntimeError("failed")))
        failed = await manager.create_job(JobType.REPORT, "tenant-a", max_attempts=1)
        worker = JobWorker(manager)
        await worker.process_one()
        assert failed.job_id in worker.dead_letter
        await worker.shutdown()
    asyncio.run(scenario())


def test_registry_validates_versioned_handlers():
    registry = JobRegistry()
    registry.register(JobType.PROFILING, lambda payload: payload, version="2")
    assert registry.validate(JobType.PROFILING, "2")
    assert not registry.validate(JobType.PROFILING, "1")
    assert registry.resolve(JobType.PROFILING, "2")({"rows": 1}) == {"rows": 1}
