"""Integration Tests for Anomaly Detection Endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_score_batch_endpoint(async_client: AsyncClient):
    payload = {
        "source_type": "auto",
        "logs": [
            '203.0.113.200 - - [25/Oct/2026:11:00:20 +0000] "GET /api/v1/products?search=shoes%27%20OR%20%271%27=%271 HTTP/1.1" 400 210 "-" "sqlmap/1.7"',
            '198.51.100.42 - - [25/Oct/2026:11:00:30 +0000] "GET /api/v1/catalog/products HTTP/1.1" 200 4500 "-" "Mozilla/5.0"',
        ]
    }
    resp = await async_client.post("/api/v1/anomalies/score-batch", json=payload)
    assert resp.status_code == 200
    anomalies = resp.json()
    # SQLi request must be flagged
    assert len(anomalies) == 1
    anom = anomalies[0]
    assert anom["risk_score"] >= 80.0
    assert anom["severity"] in ["high", "critical"]
    assert any("SQL Injection" in f for f in anom["contributing_factors"])


@pytest.mark.asyncio
async def test_list_anomalies_and_stats(async_client: AsyncClient):
    # Ingest attack log batch
    payload = {
        "source_type": "auto",
        "logs": [
            '203.0.113.200 - - [25/Oct/2026:11:00:25 +0000] "GET /api/v1/files/download?file=../../../../etc/passwd HTTP/1.1" 400 180 "-" "sqlmap/1.7"',
        ]
    }
    await async_client.post("/api/v1/ingest/raw", json=payload)

    # List anomalies
    list_resp = await async_client.get("/api/v1/anomalies")
    assert list_resp.status_code == 200
    anomalies = list_resp.json()
    assert len(anomalies) >= 1

    # Query anomaly stats
    stats_resp = await async_client.get("/api/v1/anomalies/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_anomalies"] >= 1
    assert "critical" in stats["severity_breakdown"]


@pytest.mark.asyncio
async def test_retrain_endpoint(async_client: AsyncClient):
    retrain_resp = await async_client.post("/api/v1/anomalies/retrain")
    assert retrain_resp.status_code == 200
    res = retrain_resp.json()
    assert "success" in res
    assert "models_retrained" in res
