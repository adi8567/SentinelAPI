# SentinelAPI – Intelligent API Anomaly Detection & Adaptive Protection Platform

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15%20App%20Router-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5.svg)](https://kubernetes.io/)
[![Zero Mock Data](https://img.shields.io/badge/Data-Real%20Traffic%20Only-emerald.svg)](#real-data-datasets)

SentinelAPI is an enterprise-grade API anomaly detection and closed-loop adaptive protection platform. It continuously monitors live and historical API traffic, automatically discovers endpoint schemas, learns statistical behavioral baselines, detects multi-vector anomalies in real-time using an ensemble of five detection engines, provides rich cybersecurity visualizations via a Next.js 15 SOC dashboard, and executes automated adaptive protection policies (rate limiting, temporary bans, quarantines, and SIEM forwarding).

**SentinelAPI operates strictly on real data**—no mock or synthetic data generators for core detection, baselines, or visualizations.

---

## Architecture Overview

```mermaid
flowchart TD
    subgraph Gateways["Ingestion Sources & Gateways"]
        GW1["NGINX Combined/Extended Logs"]
        GW2["Envoy / Istio JSON Telemetry"]
        GW3["AWS API Gateway CloudWatch"]
        GW4["OpenTelemetry Traces"]
        GW5["Azure APIM & GCP Endpoints"]
    end

    subgraph Ingestion["Ingestion & Streaming Pipeline"]
        ING["Universal Log Parser Registry (Auto-Detect)"]
        NORM["Normalizer & Header Sanitizer"]
        KAFKA["Apache Kafka / Redpanda Buffer"]
    end

    subgraph Storage["Analytical & Relational Storage"]
        CH["ClickHouse Columnar Database"]
        DB["DuckDB Analytical Engine"]
        PG["TimescaleDB / PostgreSQL"]
        REDIS["Redis State & Rate Limits"]
    end

    subgraph Intelligence["Detection & Learning Core"]
        INV["Automatic API Inventory Discovery"]
        BASE["Online Baseline Learner (Welford's Algorithm)"]
        subgraph Ensemble["Ensemble Anomaly Engine (0–100 Risk Score)"]
            D1["Statistical (Z-Score & MAD)"]
            D2["Isolation Forest (Unsupervised ML)"]
            D3["Markov Transition Chains"]
            D4["Contextual Identity Scorer"]
            D5["Deterministic Attack Signatures"]
        end
    end

    subgraph Protection["Adaptive Response & Policy Engine"]
        POL["Declarative Policy Engine (YAML/JSON)"]
        BAN["IP Ban & Blocklist Manager (TTL Expiration)"]
        QUAR["Client Quarantine Isolation"]
        THROT["Token Bucket Sliding-Window Throttler"]
        SIEM["CEF / Syslog SIEM Forwarder"]
    end

    subgraph Interfaces["API & Presentation Layer"]
        API["FastAPI REST & Granular RBAC Layer"]
        WS["Real-Time WebSocket Hub (/api/v1/ws/live)"]
        PROM["Prometheus Metrics (/metrics)"]
        UI["Next.js 15 SOC Cyber Dashboard"]
        GRAF["Grafana Observability Portal"]
    end

    Gateways --> ING
    ING --> NORM
    NORM --> KAFKA
    KAFKA --> CH
    KAFKA --> DB
    NORM --> INV
    INV --> BASE
    BASE --> Ensemble
    Ensemble --> POL
    POL --> BAN
    POL --> QUAR
    POL --> THROT
    POL --> SIEM
    CH --> API
    DB --> API
    Ensemble --> WS
    API --> UI
    WS --> UI
    PROM --> GRAF
```

---

## Completed Phases (Strict Sequential Order)

| Phase | Description | Status | Deliverables & Artifacts |
| :--- | :--- | :---: | :--- |
| **Phase 1** | Foundation & Real Data Ingestion | **100%** | Monorepo, FastAPI layer, log parsers, Kafka streaming, ClickHouse/DuckDB schemas |
| **Phase 2** | API Inventory & Baseline Learning | **100%** | Auto route parameterization, Welford's algorithm online learner, seasonality windows |
| **Phase 3** | Anomaly Detection Engine | **100%** | 5 ensemble detectors (Z-Score, Isolation Forest, Markov chains, Contextual, Signatures) |
| **Phase 4** | Adaptive Response & Policy Engine | **100%** | Declarative policy-as-code, token-bucket throttler, IP ban manager, SIEM CEF emission |
| **Phase 5** | Backend REST & WebSocket APIs | **100%** | Granular RBAC, JWT auth, dynamic API keys, WebSocket live streaming, forensic deep trace |
| **Phase 6** | Frontend Dashboard Visualizations | **100%** | Next.js 15 App Router, React 19, Tailwind v4, 11 real-data visualizations, forensic drawer |
| **Phase 7** | Observability, Hardening & Prod | **100%** | Prometheus exporter, OpenTelemetry tracing, Grafana dashboard, K8s HPA, NetPol, Runbooks |
| **Phase 8** | Final Integration & Handover | **100%** | E2E real-traffic test, chaos testing, 96/96 passing tests, UAC verification script |

---

## Key Capabilities & Features

### 1. Universal Real-Data Ingestion
- Ingests real access logs from NGINX, Envoy/Istio, AWS API Gateway, Azure APIM, GCP Endpoints, and OpenTelemetry traces.
- Auto-detects log formats on-the-fly and sanitizes authorization tokens, passwords, and sensitive headers.

### 2. Automatic API Inventory & Baseline Profiling
- Clusters unparameterized raw URLs (e.g. `/api/v1/users/456/profile` $\to$ `/api/v1/users/{id}/profile`).
- Maintains continuous running statistics (mean, variance, standard deviation) for request rates, latency, and payload sizes in $\mathcal{O}(1)$ time using Welford's algorithm.

### 3. Ensemble Multi-Vector Anomaly Scoring
Calculates an explainable 0–100 composite risk score using five independent models:
- **Statistical Detector**: Latency spikes and rare HTTP status codes.
- **Isolation Forest**: High-dimensional unsupervised outlier detection.
- **Markov Chains**: Evaluates transition probability across session call-chains.
- **Contextual Identity**: Evaluates client reputation, surface area traversal, and time seasonality.
- **Deterministic Signatures**: Pattern-matches SQL injection, path traversal, BOLA/IDOR, and automated vulnerability scanners (sqlmap, Nikto, Hydra).

### 4. Closed-Loop Adaptive Mitigation
- Evaluates declarative YAML/JSON policies in priority order.
- Automatically executes actions:
  - `ALLOW`: Verified benign baseline-compliant requests.
  - `THROTTLE`: Token bucket sliding-window rate limiting.
  - `CHALLENGE`: Step-up authentication or CAPTCHA challenge.
  - `BLOCK`: Immediate IP blocklist entry with automated TTL expiration or permanent ban.
  - `QUARANTINE`: Isolates client identity and restricts traffic strictly to public health endpoints.
- Emits Common Event Format (CEF) and RFC 5424 syslog messages to enterprise SIEM platforms.

### 5. Frontend Visualizations (Next.js 15 App Router)
All 11 mandatory visualizations driven by real data:
1. Real-time traffic volume time-series (stacked 2xx/3xx/4xx/5xx status codes, P95 latency).
2. Anomaly rate and threat severity over time.
3. Risk score distribution histogram (0–100) and statistical box-plot quantiles (`P25`, `P50`, `P75`, `P90`, `P95`, `P99`).
4. Top anomalous endpoints bar chart and threat heatmap.
5. API endpoint health and reliability matrix (`Healthy`, `Degraded`, `Critical`).
6. Geographic map of client IP threat origins.
7. Sequence flow diagrams and Markov attack chain graphs.
8. Latency vs. error rate scatter plots with call volume bubble sizing.
9. Client behavioral comparison table with reputation scores and one-click ban/quarantine.
10. Live incident alert timeline with severity filters and analyst workflows.
11. ML ensemble model performance metrics with live retraining trigger.
- **Forensic Deep Inspection Drawer**: Verbatim raw log inspection, contributing detector scores, and explainability vectors.
- **Real Data Stream Ingestion Console**: 1-click execution of real datasets directly from the browser.

---

## Quick Start & Running Locally

### Prerequisites
- Python 3.12+
- Node.js 20+ & npm 10+
- (Optional) Docker & Docker Compose

### 1. Backend Setup & Startup
```powershell
# Clone and navigate to repository
cd sentinelapi

# Activate Python virtual environment
.venv\Scripts\Activate.ps1   # Windows PowerShell
# or: source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r backend/requirements.txt

# Run all backend unit & integration tests (96 tests)
pytest backend/tests -v

# Start FastAPI backend server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger OpenAPI Docs: `http://localhost:8000/api/v1/docs`
- Prometheus Metrics Endpoint: `http://localhost:8000/metrics`

### 2. Frontend Setup & Startup
```powershell
cd frontend

# Install dependencies
npm install

# Run production build check
npm run build

# Start Next.js 15 development server
npm run dev
```
- Open **`http://localhost:3000`** in your browser.

---

## Turnkey Production Deployment (Docker Compose)

Launch the entire platform (Backend, Frontend, Kafka, ClickHouse, TimescaleDB, Redis, Prometheus, Grafana) with a single command:

```bash
cd infrastructure/docker
docker compose up -d --build
```

### Accessing Portals:
- **SOC Cyber Dashboard**: `http://localhost:3000`
- **FastAPI Core & OpenAPI Docs**: `http://localhost:8000/api/v1/docs`
- **Prometheus Telemetry Scraper**: `http://localhost:9090`
- **Grafana Security Operations**: `http://localhost:3001` (admin / sentineladmin)

---

## User Acceptance Criteria (UAC) Verification

Execute the automated verification script:
```powershell
python scripts/verify_uac.py
```

```
================================================================================
 SENTINELAPI PLATFORM – USER ACCEPTANCE CRITERIA (UAC) AUDIT
================================================================================
[+] Phase 1: Real-Data Ingestion Pipeline           [PASS] (4/4 checks)
[+] Phase 2: API Inventory & Baseline Learning      [PASS] (4/4 checks)
[+] Phase 3: Real-Time Anomaly Detection Engine     [PASS] (5/5 checks)
[+] Phase 4: Adaptive Response & Policy Engine      [PASS] (5/5 checks)
[+] Phase 5: Backend REST & WebSocket APIs          [PASS] (6/6 checks)
[+] Phase 6: Frontend Dashboard Visualizations      [PASS] (14/14 checks)
[+] Phase 7: Observability & Production Ready       [PASS] (8/8 checks)
[+] Phase 8: Final Integration, Testing & Handover  [PASS] (4/4 checks)
================================================================================
 AUDIT RESULT: 50 / 50 CRITERIA PASSED (100.0%)
 VERDICT: READY FOR PRODUCTION DEPLOYMENT & PLATFORM HANDOVER
================================================================================
```

---

## Real Data Datasets

Located in `data/real_datasets/`:
- `nginx_access.log`: Real NGINX combined and extended access logs.
- `envoy_access.json`: Real Envoy gateway structured JSON access logs.
- `aws_api_gateway.json`: Real AWS API Gateway CloudWatch access logs.
- `real_api_sec_attacks.log`: Actual adversarial attack traces containing SQL injection, directory traversal, BOLA/IDOR resource enumeration, and automated vulnerability scanners.
- `azure_apim.json`, `kong_gateway.json`, `gcp_endpoints.json`, `otel_traces.json`.

---

## Technical Documentation
- [System Architecture & Reference](docs/architecture.md)
- [Production Deployment Guide](docs/deployment.md)
- [Operational SRE & SOC Runbooks](docs/runbooks.md)
- [Performance Benchmarking & Tuning](docs/performance_tuning.md)

---

## License
Apache License 2.0. Built for production-grade API security.
