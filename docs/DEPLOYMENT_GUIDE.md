# AI Data Analyst OS — Production Deployment Guide

## Prerequisites
- Docker Engine $\ge 24.0$
- Docker Compose $\ge 2.20$
- Python $\ge 3.11$ (for local development & CLI operations)
- Minimum 4 CPU cores, 8 GB RAM

---

## Quickstart (Single Command)

```bash
docker compose up -d --build
```

Verify service health:
```bash
curl http://localhost:8000/api/v1/health
```

---

## Production Deployment Steps

### 1. Configure Environment Variables
Copy and customize the production profile:
```bash
cp .env.production .env
```
Ensure strong secrets are defined:
- `JWT_SECRET_KEY`: At least 32 cryptographically random characters
- `POSTGRES_PASSWORD`: Strong master password
- `DEBUG`: Set to `false`

### 2. Database Migrations
Execute Alembic schema migration to create all tables:
```bash
python -m alembic upgrade head
```

### 3. Deploy Containers with Zero Downtime
Run the automated deployment script:
```bash
python scripts/deploy.py --version v1.0.0
```

### 4. Post-Deployment Verification
Check endpoint health and Prometheus metrics:
```bash
curl -I http://localhost:8000/api/v1/health
curl http://localhost:8000/metrics
```

### 5. Automated Rollback (In Case of Incidents)
If health checks degrade, initiate instant rollback:
```bash
python scripts/rollback.py --target v1.0.0 --reason "Latency threshold breached"
```
