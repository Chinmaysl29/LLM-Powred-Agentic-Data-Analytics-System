# Enterprise AI Data Analyst OS

This repository contains the Phase 1 backend foundation for a production-grade enterprise AI Data Analyst platform. It provides a versioned FastAPI gateway, typed configuration, PostgreSQL, Redis, and ChromaDB adapters, request middleware, structured logging, lifecycle management, health checks, and a testing foundation.

## Run with Docker

```powershell
cd ai-data-analyst-os
Copy-Item .env.example .env
docker compose up --build
```

Open the frontend at `http://localhost:5173` and the API health endpoint at
`http://localhost:8000/api/v1/health`.

The Docker services use the Compose network, so PostgreSQL is always available
to the backend at `postgres:5432`. The `POSTGRES_HOST_PORT` value only controls
the optional PostgreSQL port exposed on the developer's computer. If port 5432
is already in use, set `POSTGRES_HOST_PORT=5433` in `.env` before starting.

Stop the stack with `docker compose down`. Add `--volumes` only when you want to
remove the local PostgreSQL data.

## Run without Docker

```powershell
cd ai-data-analyst-os
python -m pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Run the backend test suite with:

```powershell
docker compose exec backend pytest -q
```

Health: `GET /api/v1/health`. Runtime logs are written to `logs/app.log`.

Phase 15 autonomous intelligence is available as a decision-support API at
`/api/v1/autonomous`. See [Phase 15 readiness](docs/PHASE15_READINESS.md) for
the current production gap and the recommended implementation sequence.
