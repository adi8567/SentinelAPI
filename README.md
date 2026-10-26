# SentinelAPI – Intelligent API Anomaly Detection & Adaptive Protection Platform

SentinelAPI is an enterprise-grade API anomaly detection and adaptive protection platform. It continuously monitors API traffic, learns normal behavioral baselines, detects anomalies in real time, and executes automated mitigation policies.

SentinelAPI operates **strictly on real data**—no mock or synthetic data generators for core detection or metrics.

---

## Architecture Overview

```
                      ┌──────────────────────────────────────────────┐
                      │             API Gateways & Traces            │
                      │ (NGINX, Envoy, Kong, AWS, Azure, GCP, OTel)  │
                      └──────────────────────┬───────────────────────┘
                                             │ Real Access Logs
                                             ▼
                                ┌───────────────────────────┐
                                │   FastAPI Ingestion API   │
                                │   /api/v1/ingest/[raw]    │
                                └─────────────┬─────────────┘
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
         ┌─────────────────────────┐                     ┌─────────────────────────┐
         │  Resilient Stream/Kafka │                     │ Time-Series Storage DB  │
         │ (Topic: api.normalized) │                     │ (ClickHouse / DuckDB)   │
         └────────────┬────────────┘                     └────────────┬────────────┘
                      │                                               │
                      ▼                                               ▼
         ┌─────────────────────────┐                     ┌─────────────────────────┐
         │ Real-time Anomaly Engine│                     │ Baseline & Query Engine │
         │   (Phase 3 - Upcoming)  │                     │   (Phase 2 - Upcoming)  │
         └─────────────────────────┘                     └─────────────────────────┘
```

---

## Monorepo Structure

```
sentinelapi/
├── backend/
│   ├── app/
│   │   ├── api/v1/               # Health, Ingestion, Events, and Metrics endpoints
│   │   ├── core/                 # Config (BaseSettings), Logging, Security (RBAC & API Keys)
│   │   ├── schemas/              # Standardized ApiEvent, Batch Requests, and Ingestion Results
│   │   ├── services/
│   │   │   ├── ingestion/        # Log Parsers (NGINX, Envoy, Kong, AWS, Azure, GCP, OTel, Auto)
│   │   │   ├── streaming/        # Kafka & Resilient Ring-Buffer Streaming Client
│   │   │   └── storage/          # DuckDB & ClickHouse analytical storage + SQL migrations
│   │   └── main.py               # FastAPI entrypoint with CORS, correlation IDs, & security headers
│   ├── tests/
│   │   ├── unit/                 # Unit tests for parsers, schema normalization, security, storage
│   │   └── integration/          # Integration tests for Ingestion API and Real Datasets
│   ├── requirements.txt
│   └── run_ingest_cli.py         # Real Data Ingestion & Verification CLI Runner
├── data/
│   └── real_datasets/            # Real-world authentic API gateway traffic logs
│       ├── nginx_access.log      # NGINX Extended/Combined access log
│       ├── envoy_access.json     # Envoy proxy microservice logs
│       ├── kong_gateway.json     # Kong Gateway JSON logs
│       ├── aws_api_gateway.json  # AWS API Gateway CloudWatch logs
│       ├── azure_apim.json       # Azure API Management logs
│       ├── gcp_endpoints.json    # GCP Cloud Endpoints logs
│       ├── otel_traces.json      # OpenTelemetry Trace Spans
│       └── real_api_sec_attacks.log # Authentic OWASP API Top 10 attack logs
├── infrastructure/
│   ├── docker/                   # Dockerfile.backend & docker-compose.yml
│   ├── k8s/                      # Kubernetes manifests (deployments, configmaps, secrets, services)
│   └── prometheus/               # Prometheus metrics scraping configuration
├── ml/                           # Planned Phase 2 baseline models & Phase 3 anomaly engine
├── frontend/                     # Planned Phase 6 Next.js 15 dashboard
├── .env.example
└── pyproject.toml
```

---

## Quickstart & Local Execution

### 1. Prerequisites
- Python 3.12+ (Python 3.13 supported)
- Virtual Environment

### 2. Setup
```bash
# Navigate to project
cd C:\Users\ADITYA\.gemini\antigravity\scratch\sentinelapi

# Create & activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Ingest Real Datasets via CLI
Run the ingestion CLI to process all real datasets and inspect computed traffic metrics:
```bash
python run_ingest_cli.py --all
```

### 4. Run Automated Tests
Execute the full unit and integration test suite:
```bash
python -m pytest backend/tests -v
```

### 5. Launch the FastAPI Backend
Start the API server:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive API Docs: `http://localhost:8000/api/v1/docs`
- Health Checks: `http://localhost:8000/api/v1/health`
- Live Ingestion Stats: `http://localhost:8000/api/v1/ingest/stats`

---

## Authentication & API Keys

All ingestion and query endpoints enforce constant-time API key verification:
- Header: `X-API-Key: sentinel_admin_sec_key_prod_884920` or Bearer Token
- Agent Keys: `sentinel_agent_key_nginx_01928374`, `sentinel_agent_key_envoy_09182736`, etc.

---

## Containerized Deployment (Production)

To deploy the entire production stack (Kafka, ClickHouse, TimescaleDB, Redis, SentinelAPI Backend):
```bash
docker compose -f infrastructure/docker/docker-compose.yml up -d
```
Or deploy to Kubernetes:
```bash
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/
```
