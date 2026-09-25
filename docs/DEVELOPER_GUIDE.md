# AI Data Analyst OS — Developer Onboarding Guide

## Introduction
This guide contains complete instructions for a new developer to set up, build, test, and contribute to the **AI Data Analyst OS** repository from scratch.

---

## 1. Local Environment Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Docker Engine & Docker Compose
- Git

### Clone & Navigate
```bash
git clone https://github.com/enterprise/ai-data-analyst-os.git
cd ai-data-analyst-os
```

### Python Virtual Environment
```bash
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate
```

### Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install pytest pytest-cov
```

### Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

---

## 2. Environment Configuration
Copy the development environment template:
```bash
cp .env.example .env
```
Default connection strings are pre-configured to work with the standard Docker stack.

---

## 3. Launching Infrastructure Services
Start the PostgreSQL, Redis, and ChromaDB containers:
```bash
docker compose up -d postgres redis chromadb
```

Verify services are up:
```bash
docker compose ps
```

---

## 4. Running Backend & Frontend Locally

### Start Backend API Server
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger docs will be available at `http://localhost:8000/docs`.

### Start Frontend Vite Dev Server
```bash
cd frontend
npm run dev
```
Web app will be available at `http://localhost:5173`.

---

## 5. Running the Test Suite
Execute the entire test suite:
```bash
pytest tests/ -v
```

Run specific test phases:
```bash
pytest tests/ -k phase9 -v
pytest tests/ -k phase10 -v
```

---

## 6. Code Architecture Conventions
- `backend/agents/`: LLM-driven multi-agent implementations.
- `backend/orchestrator/`: Task routing, intent classification, and execution graph.
- `backend/sql_agent/`: Natural language to SQL compiler with strict safety guardrails.
- `backend/rag/`: Retrieval-Augmented Generation pipeline (chunking, vector stores, hybrid retrievers).
- `backend/forecasting/`: Predictive modeling (ARIMA, Prophet, XGBoost).
- `backend/recommendations/`: Business decision and optimization intelligence engines.
- `backend/deployment/`: Production operations, CI/CD, backup, security, and certification.
