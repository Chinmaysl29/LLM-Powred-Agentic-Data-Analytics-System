# Phase 16 operations guide

Phase 16 provides the infrastructure that must be in place before Phase 17.

## 16.1 Database migrations

Use [the migration workflow](DATABASE_MIGRATIONS.md). Alembic tracks the
applied revision in `alembic_version`; the Phase 16 audit-table revision is
`002_phase16_audit_trail`.

## 16.2 Cache layer

`EnterpriseCache` accepts the application-owned `RedisCache` adapter. It
provides tenant-isolated dataset, analytics, forecast, query, and session
keys, namespace TTL policies, warming, prefix invalidation, and L1 fallback.
No service should create its own Redis client.

## 16.3 Background jobs

`BackgroundJobManager` stores job metadata in Redis and queue IDs in a Redis
list. Register an EDA, forecast, report, or RAG handler in the worker process,
then repeatedly call `run_next()`. Job events are retried up to their explicit
`max_attempts` and retain terminal failure details.

## 16.4 Monitoring

Prometheus scrapes `GET /metrics`. It includes API request count and latency,
dependency health, agent executions, and background-job state transitions.

## 16.5 Audit trail

`AuditTrailMiddleware` captures successful dataset, forecast, agent,
authentication, and general API actions. Events are stored in PostgreSQL after
migration and fall back to process memory during an infrastructure outage.
Query the audit API with `GET /api/v1/audit`; use `POST /api/v1/audit` for
explicit business events.
