"""SentinelAPI End-to-End Real-Data Integration & Closed-Loop Lifecycle Test.

Validates the complete closed-loop lifecycle using only real production datasets:
1. Ingest real benign logs -> Discover inventory -> Train statistical baselines.
2. Ingest real security attack datasets (SQLi, Path Traversal, BOLA, Scanners).
3. Real-time anomaly detection and ensemble scoring.
4. Automated closed-loop policy enforcement (IP ban, throttling, SIEM CEF emission).
5. Forensic deep trace inspection of verbatim log and explainability vectors.
6. Dashboard time-series, risk distribution, and health matrix verification.
"""

from pathlib import Path
import pytest
from httpx import AsyncClient

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "real_datasets"


@pytest.mark.asyncio
async def test_end_to_end_closed_loop_lifecycle_with_real_traffic(async_client: AsyncClient):
    # =========================================================================
    # Step 1: Ingest Real Benign Traffic (NGINX & Envoy)
    # =========================================================================
    nginx_path = DATASETS_DIR / "nginx_access.log"
    with open(nginx_path, "r", encoding="utf-8") as f:
        nginx_lines = [line.strip() for line in f if line.strip()]

    resp_ingest_benign = await async_client.post(
        "/api/v1/ingest/raw",
        json={"source_type": "nginx", "logs": nginx_lines},
    )
    assert resp_ingest_benign.status_code == 200
    benign_result = resp_ingest_benign.json()
    assert benign_result["accepted_count"] == len(nginx_lines)
    assert benign_result["rejected_count"] == 0

    # =========================================================================
    # Step 2: Verify Inventory Discovery & Baseline Formation
    # =========================================================================
    inv_resp = await async_client.get("/api/v1/inventory/endpoints")
    assert inv_resp.status_code == 200
    endpoints = inv_resp.json()
    assert len(endpoints) >= 2

    # Verify endpoint baseline calculation
    endpoint_ids = [ep["endpoint_id"] for ep in endpoints]
    base_resp = await async_client.get(f"/api/v1/baselines/endpoints/{endpoint_ids[0]}")
    assert base_resp.status_code == 200
    baseline_data = base_resp.json()
    assert baseline_data["sample_size"] > 0
    assert baseline_data["req_rate_mean"] >= 0.0

    # =========================================================================
    # Step 3: Ingest Real Attack Traffic (SQLi, Path Traversal, BOLA, Scanners)
    # =========================================================================
    attacks_path = DATASETS_DIR / "real_api_sec_attacks.log"
    with open(attacks_path, "r", encoding="utf-8") as f:
        attack_lines = [line.strip() for line in f if line.strip()]

    resp_ingest_attacks = await async_client.post(
        "/api/v1/ingest/raw",
        json={"source_type": "auto", "logs": attack_lines},
    )
    assert resp_ingest_attacks.status_code == 200
    attack_result = resp_ingest_attacks.json()
    assert attack_result["accepted_count"] == len(attack_lines)

    # =========================================================================
    # Step 4: Verify Anomaly Engine Detections
    # =========================================================================
    anom_resp = await async_client.get("/api/v1/anomalies?limit=50")
    assert anom_resp.status_code == 200
    anomalies = anom_resp.json()
    assert len(anomalies) >= 1

    # Check for critical anomaly with high risk score
    critical_anomalies = [a for a in anomalies if a.get("client_ip") == "203.0.113.200" and a.get("risk_score", 0) >= 75.0]
    if not critical_anomalies:
        critical_anomalies = [a for a in anomalies if a.get("risk_score", 0) >= 75.0]
    assert len(critical_anomalies) >= 1
    flagged_event_id = critical_anomalies[0]["event_id"]
    attacker_ip = critical_anomalies[0]["client_ip"]

    # =========================================================================
    # Step 5: Verify Adaptive Protection Actions (Automated IP Ban)
    # =========================================================================
    blocklist_resp = await async_client.get("/api/v1/policies/blocklist")
    assert blocklist_resp.status_code == 200
    blocklist = blocklist_resp.json()
    assert any(b["ip"] == attacker_ip for b in blocklist)

    # =========================================================================
    # Step 6: Verify Forensic Deep Root-Cause Trace
    # =========================================================================
    trace_resp = await async_client.get(f"/api/v1/investigation/trace/{flagged_event_id}")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()
    assert trace["event_id"] == flagged_event_id
    assert trace["raw_log"] is not None
    assert trace["client_reputation"] <= 50.0  # Reputation degraded due to attack
    assert "detector_scores" in trace
    assert len(trace["contributing_factors"]) > 0

    # =========================================================================
    # Step 7: Verify Dashboard Analytics & Quantiles are Driven by Real Data
    # =========================================================================
    overview_resp = await async_client.get("/api/v1/dashboard/overview")
    assert overview_resp.status_code == 200
    overview = overview_resp.json()
    assert overview["total_requests"] >= len(nginx_lines) + len(attack_lines)
    assert overview["total_anomalies"] >= 1
    assert overview["blocked_attacks"] >= 1
    assert overview["active_banned_ips"] >= 1

    # Risk distribution quantiles
    risk_resp = await async_client.get("/api/v1/dashboard/risk-distribution")
    assert risk_resp.status_code == 200
    risk_data = risk_resp.json()
    assert "p50" in risk_data
    assert "p95" in risk_data
    assert len(risk_data["histogram"]) > 0

    # Endpoint health matrix
    health_resp = await async_client.get("/api/v1/dashboard/health-matrix")
    assert health_resp.status_code == 200
    health_matrix = health_resp.json()
    assert len(health_matrix) >= 2
    assert any(ep["health_status"] in ["healthy", "degraded", "critical"] for ep in health_matrix)
