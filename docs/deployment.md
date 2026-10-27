# SentinelAPI Production Deployment Guide

This guide details deployment options for SentinelAPI across local, staging, and enterprise Kubernetes production environments.

---

## 1. Quick Start with Docker Compose

SentinelAPI includes a turnkey, production-mirrored Docker Compose configuration containing all infrastructure components:
- FastAPI Core Service (`sentinel-backend`: port 8000)
- Next.js 15 SOC Cyber Dashboard (`sentinel-frontend`: port 3000)
- Apache Kafka Broker & Zookeeper (ports 9092, 2181)
- ClickHouse Columnar Database (ports 8123, 9000)
- TimescaleDB / PostgreSQL (port 5432)
- Redis Cache & Throttler (port 6379)
- Prometheus Telemetry Scraper (port 9090)
- Grafana Threat Visualizer (port 3001)

### Starting the Full Stack
```bash
cd infrastructure/docker
docker compose up -d --build
```

### Verifying Service Health
```bash
docker compose ps
curl -s http://localhost:8000/api/v1/health | jq .
curl -s http://localhost:8000/metrics | head -n 20
```

### Accessing Portals:
- **Next.js 15 Dashboard**: `http://localhost:3000`
- **FastAPI OpenAPI / Swagger**: `http://localhost:8000/api/v1/docs`
- **Grafana Security Operations**: `http://localhost:3001` (admin / sentineladmin)
- **Prometheus Telemetry**: `http://localhost:9090`

---

## 2. Enterprise Kubernetes Deployment

Production manifests are located in `infrastructure/k8s/`.

### Deployment Steps:
1. **Create Namespace**:
   ```bash
   kubectl apply -f infrastructure/k8s/namespace.yaml
   ```

2. **Deploy Configuration & Secrets**:
   ```bash
   kubectl apply -f infrastructure/k8s/configmap.yaml
   kubectl apply -f infrastructure/k8s/secrets.yaml
   ```

3. **Deploy Core Backend Service**:
   ```bash
   kubectl apply -f infrastructure/k8s/backend-deployment.yaml
   kubectl apply -f infrastructure/k8s/services.yaml
   ```

4. **Deploy SOC Cyber Frontend**:
   ```bash
   kubectl apply -f infrastructure/k8s/frontend-deployment.yaml
   ```

5. **Apply Security Hardening & Zero-Trust Network Policies**:
   ```bash
   kubectl apply -f infrastructure/k8s/rbac.yaml
   kubectl apply -f infrastructure/k8s/network-policy.yaml
   ```

6. **Enable Horizontal Pod Autoscaler (HPA)**:
   ```bash
   kubectl apply -f infrastructure/k8s/hpa.yaml
   ```

---

## 3. Hardware Sizing & Capacity Guidelines

| Deployment Tier | Events / Sec | CPU (Backend) | RAM (Backend) | ClickHouse Disk |
| :--- | :--- | :--- | :--- | :--- |
| **Small / Edge** | Up to 1,000 req/s | 2 vCPU | 2 GB | 100 GB NVMe |
| **Medium** | 1,000 – 10,000 req/s | 4 – 8 vCPU | 8 – 16 GB | 500 GB NVMe |
| **Large / Enterprise** | 10,000 – 100,000+ req/s | 16 – 32 vCPU (HPA 3–20 pods) | 32 – 64 GB | 2 TB+ NVMe RAID |

---

## 4. Environment Variables Reference

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Deployment stage (`development`, `staging`, `production`) |
| `STORAGE_BACKEND` | `duckdb` (or `clickhouse`) | Analytical columnar storage engine selector |
| `STREAMING_BACKEND` | `memory` (or `kafka`) | Message streaming bus selector |
| `CLICKHOUSE_HOST` | `localhost` | ClickHouse server hostname or IP |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker bootstrap list |
| `ADMIN_API_KEY` | (Required in prod) | Primary administrative secret token |
| `SECRET_KEY` | (Required in prod) | JWT token signing key (HS256) |
| `LOG_FORMAT` | `json` | Logging format (`text` or `json`) |
