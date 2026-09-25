# AI Data Analyst OS — API Documentation

## Overview
The AI Data Analyst OS backend exposes a high-performance, asynchronous REST API via FastAPI, designed for automated business intelligence, natural language dataset querying, forecasting, and decision analytics.

- **Base URL**: `http://localhost:8000/api/v1`
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc UI**: `http://localhost:8000/redoc`

---

## Authentication
All protected endpoints require an HTTP Bearer JWT token in the `Authorization` header:
```http
Authorization: Bearer <access_token>
```

### 1. Issue Token Pair
- **Endpoint**: `POST /api/v1/auth/token`
- **Request Body**:
  ```json
  {
    "user_id": "usr_991",
    "email": "analyst@enterprise.com",
    "role": "analyst"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 3600
  }
  ```

---

## Datasets & Analytics Endpoints

### 2. Upload & Ingest Dataset
- **Endpoint**: `POST /api/v1/datasets/upload`
- **Payload**: Multipart form data with file attachment (`.csv`, `.xlsx`, `.parquet`).
- **Response**: `201 Created`
  ```json
  {
    "dataset_id": "ds_8f29c",
    "filename": "q3_financials.csv",
    "row_count": 10500,
    "columns": ["date", "department", "revenue", "cost"],
    "quality_score": 98.4
  }
  ```

### 3. Ask Natural Language Question
- **Endpoint**: `POST /api/v1/analytics/query`
- **Request**:
  ```json
  {
    "dataset_id": "ds_8f29c",
    "query": "What are the top 3 revenue departments this quarter?"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "sql": "SELECT department, SUM(revenue) FROM sales GROUP BY department ORDER BY 2 DESC LIMIT 3",
    "result": [
      {"department": "Enterprise Cloud", "sum": 4500000},
      {"department": "Consulting", "sum": 2800000},
      {"department": "Hardware", "sum": 1900000}
    ],
    "explanation": "Enterprise Cloud contributed the highest revenue at $4.5M."
  }
  ```

### 4. Generate Multi-Model Time Series Forecast
- **Endpoint**: `POST /api/v1/forecasting/predict`
- **Request**:
  ```json
  {
    "dataset_id": "ds_8f29c",
    "target_column": "revenue",
    "date_column": "date",
    "model_type": "auto",
    "horizon": 30
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "best_model": "Prophet",
    "mape": 0.042,
    "forecast": [125000, 127000, 131000],
    "lower_bound": [118000, 120000, 123000],
    "upper_bound": [132000, 134000, 139000]
  }
  ```

### 5. Generate Executive Report
- **Endpoint**: `POST /api/v1/reports/generate`
- **Payload**:
  ```json
  {
    "report_type": "Executive Summary",
    "format": "pdf",
    "dataset_id": "ds_8f29c"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "report_id": "rep_102",
    "file_url": "/reports/download/rep_102.pdf",
    "status": "ready"
  }
  ```
