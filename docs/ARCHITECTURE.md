# AI Data Analyst OS — System Architecture

## Architecture Overview
The platform uses a layered micro-modular architecture optimized for low-latency analytics, high-throughput time-series forecasting, and natural language question answering.

```mermaid
graph TD
    Client[Web Browser / CLI / API] --> Ingress[Nginx Load Balancer / Ingress]
    Ingress --> Frontend[React / Vite SPA]
    Ingress --> Gateway[FastAPI Gateway / Auth / Rate Limiter]
    
    subgraph Core Backend Services
        Gateway --> Orchestrator[Enterprise Orchestrator & Task Router]
        Orchestrator --> SQLAgent[SQL Intelligence & Guardrails]
        Orchestrator --> RAG[Hybrid RAG Engine: BM25 + Dense Embeddings]
        Orchestrator --> ForecastEngine[Forecasting Pipeline: ARIMA / Prophet / XGBoost]
        Orchestrator --> Decisions[Decision Intelligence & Optimization]
    end

    subgraph Storage & Cache Tier
        SQLAgent --> Postgres[(PostgreSQL 16 High Availability)]
        ForecastEngine --> Redis[(Redis 7 Cluster & Cache)]
        RAG --> Chroma[(ChromaDB Vector Store)]
    end
```

---

## Component Breakdown

1. **Ingress & Load Balancer**:
   - SSL termination and HTTP/2 proxying via Nginx.
   - Rate limiting (120 req/min with burst buffer).

2. **Frontend Layer**:
   - React with Vite, state management via lightweight hooks, real-time KPI dashboards, and interactive chart visualizations.

3. **Backend API Gateway**:
   - FastAPI asynchronous runtime.
   - JWT authentication, RBAC authorization, and request telemetry metrics.

4. **Intelligence Tier**:
   - **SQL Agent**: Translates English questions to ANSI SQL with 100% destructive mutation blocking.
   - **RAG Engine**: Hybrid retrieval combining BM25 keyword matching with dense embeddings.
   - **Forecasting Engine**: Auto-selects between Auto-ARIMA, Facebook Prophet, and XGBoost based on historical cross-validation.
   - **Decision Engine**: Generates actionable business recommendations, cost optimizations, and pricing adjustments.

5. **Data & Persistence Layer**:
   - **PostgreSQL 16**: Primary transaction store, datasets metadata, and audit logging.
   - **Redis 7**: Distributed caching, token blacklists, and rate-limiting counters.
   - **ChromaDB**: Semantic vector embeddings store for documentation and unstructured text.
