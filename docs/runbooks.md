# SentinelAPI Operational Runbooks (SRE & SOC)

This document contains step-by-step procedures for Site Reliability Engineers (SRE) and Security Operations Center (SOC) analysts operating SentinelAPI in production.

---

## Runbook 1: High Ingestion Lag & Kafka Backpressure

### Symptoms
- Prometheus alert: `SentinelKafkaConsumerLagHigh` (Lag > 50,000 events).
- Dashboard overview shows a delay in real-time traffic volume updates.

### Triage & Resolution Steps
1. **Inspect Kafka Consumer Lag**:
   ```bash
   kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group sentinel-ingestion-workers
   ```
2. **Scale Ingestion Pods**:
   - In Kubernetes, increase backend replica count:
     ```bash
     kubectl scale deployment sentinelapi-backend --replicas=10 -n sentinelapi
     ```
3. **Verify ClickHouse Ingestion Bottlenecks**:
   - Check active queries in ClickHouse:
     ```sql
     SELECT query_id, elapsed, query FROM system.processes WHERE elapsed > 5;
     ```
   - If ClickHouse buffer flush latency is high, tune `max_insert_block_size=100000` in `config.xml`.

---

## Runbook 2: False Positive Remediation & Baseline Adjustment

### Symptoms
- A legitimate internal microservice or VIP client is being throttled or flagged with risk scores > 80.

### Triage & Resolution Steps
1. **Identify Client IP and Endpoint**:
   - Open the **Alerts Timeline** or run:
     ```bash
     curl -s -H "X-API-Key: $ADMIN_KEY" "http://localhost:8000/api/v1/alerts/?status=new&severity=critical" | jq .
     ```
2. **Mark Alert as False Positive**:
   - In the frontend UI, click **False Positive**, or send API patch:
     ```bash
     curl -X PATCH -H "X-API-Key: $ADMIN_KEY" \
       -H "Content-Type: application/json" \
       -d '{"status": "false_positive", "analyst_notes": "Internal payment sync service"}' \
       http://localhost:8000/api/v1/alerts/<ALERT_ID>
     ```
3. **Add Allow Policy Override**:
   - Append an allow policy in `policies/default_policies.yaml` for the client IP or service account identity with priority 1.

---

## Runbook 3: Emergency Attacker IP Unban & Whitelist

### Procedure
1. **Check Active Blocklist**:
   ```bash
   curl -s -H "X-API-Key: $ADMIN_KEY" http://localhost:8000/api/v1/policies/blocklist | jq .
   ```
2. **Remove Unintentional IP Block**:
   ```bash
   curl -X DELETE -H "X-API-Key: $ADMIN_KEY" http://localhost:8000/api/v1/policies/blocklist/<IP_ADDRESS>
   ```
3. **Verify Client Can Connect**:
   - Check that `reputation_score` recovers and no active ban blocks the request.

---

## Runbook 4: Zero-Downtime Model Retraining

### Procedure
When a new API version is released with major structural changes:
1. **Trigger Online Baseline Learner Batch Recalibration**:
   - In the frontend **ML Engine & Live Ingestion** tab, click **Trigger Model Retrain**, or execute:
     ```bash
     curl -X POST -H "X-API-Key: $ADMIN_KEY" http://localhost:8000/api/v1/anomalies/retrain
     ```
2. **Verify Training Metrics**:
   - Inspect `ModelPerformanceMetrics` for updated version tags and sub-millisecond inference times.

---

## Runbook 5: Database Disaster Recovery & Restore

### Restore Procedure from Archive
1. **Locate Latest Valid Archive**:
   ```bash
   ls -lat /var/backups/sentinelapi/sentinelapi_backup_*.tar.gz | head -n 1
   ```
2. **Extract Archive**:
   ```bash
   tar -xzf sentinelapi_backup_<TIMESTAMP>.tar.gz -C /tmp/restore/
   ```
3. **Restore TimescaleDB / PostgreSQL**:
   ```bash
   pg_restore -h localhost -p 5432 -U postgres -d sentinelapi --clean --if-exists /tmp/restore/*/timescale_sentinelapi.dump
   ```
4. **Restore DuckDB Database**:
   ```bash
   cp /tmp/restore/*/sentinelapi.duckdb ./data/sentinelapi.duckdb
   ```
5. **Restart Backend Service**:
   ```bash
   kubectl rollout restart deployment sentinelapi-backend -n sentinelapi
   ```
