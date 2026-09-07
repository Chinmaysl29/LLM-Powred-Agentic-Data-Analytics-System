# Database migrations

Schema changes are managed only through Alembic. The migration environment
uses `backend.app.core.config.Settings`, so `DATABASE_URL` (or the existing
`POSTGRES_*` variables) remains the only database configuration source.

## Commands

Run locally:

```powershell
python scripts/migrate.py current
python scripts/migrate.py revision --autogenerate --message "add audit trail"
python scripts/migrate.py upgrade head
python scripts/migrate.py downgrade -1
```

Run in Docker:

```powershell
docker compose exec backend python scripts/migrate.py upgrade head
```

## Production workflow

1. Change SQLAlchemy models.
2. Generate a revision with `--autogenerate`.
3. Review both `upgrade()` and `downgrade()` before committing.
4. Run the migration validation tests and apply the migration in staging.
5. Back up the production database, then run `upgrade head` as a deploy step.
6. Verify `current` matches the expected revision and application health checks.

Never edit an already-deployed migration. Add a new forward-only revision;
production downgrades are an emergency recovery action after compatibility and
data-loss review.
