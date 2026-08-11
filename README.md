# Enterprise AI Data Analyst OS

This repository follows the supplied seven-phase architecture. Phase 1 is the active implementation: a FastAPI service, PostgreSQL-ready configuration, dataset upload, and raw dataset storage.

## Run with Docker

```powershell
cd ai-data-analyst-os
Copy-Item .env.example .env
docker compose up --build
```

Open the frontend at `http://localhost:5173` and the API health endpoint at
`http://localhost:8000/health`.

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

Health: `GET /health`  
Upload: `POST /api/datasets/upload` with multipart field `file`.

Later-phase directories are intentionally kept as stable integration boundaries and are not implemented yet.
