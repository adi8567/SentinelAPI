"""Integration Tests for FastAPI Ingestion Endpoints."""

import pytest
from httpx import AsyncClient
from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_health_endpoints(async_client: AsyncClient):
    # Liveness
    live_resp = await async_client.get("/api/v1/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "alive"

    # Readiness
    ready_resp = await async_client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"

    # Overall Health
    health_resp = await async_client.get("/api/v1/health")
    assert health_resp.status_code == 200
    data = health_resp.json()
    assert data["status"] in ["ok", "healthy"]
    assert "components" in data


@pytest.mark.asyncio
async def test_authentication_required(async_client: AsyncClient):
    # Request without auth header should fail with 401
    transport_unauth = async_client._transport
    from httpx import AsyncClient as RawClient
    async with RawClient(transport=transport_unauth, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/ingest/stats")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ingest_raw_batch_endpoint(async_client: AsyncClient):
    payload = {
        "source_type": "auto",
        "gateway_id": "test-gw",
        "logs": [
            '198.51.100.42 - - [25/Oct/2026:10:00:01 +0000] "GET /api/v1/health HTTP/1.1" 200 48 "-" "kube-probe/1.28"',
            '203.0.113.15 - - [25/Oct/2026:10:00:05 +0000] "POST /api/v1/auth/login HTTP/1.1" 200 642 "-" "Mozilla/5.0" 0.085 0.082 340',
        ]
    }
    resp = await async_client.post("/api/v1/ingest/raw", json=payload)
    assert resp.status_code == 200
    result = resp.json()
    assert result["success"] is True
    assert result["accepted_count"] == 2
    assert result["rejected_count"] == 0
    assert result["source_detected"] == "nginx"


@pytest.mark.asyncio
async def test_ingest_file_endpoint(async_client: AsyncClient):
    log_content = (
        '198.51.100.42 - - [25/Oct/2026:10:00:01 +0000] "GET /api/v1/test1 HTTP/1.1" 200 48 "-" "curl/7.88.1"\n'
        '198.51.100.43 - - [25/Oct/2026:10:00:02 +0000] "POST /api/v1/test2 HTTP/1.1" 201 100 "-" "curl/7.88.1"\n'
    )
    files = {"file": ("test_access.log", log_content.encode("utf-8"), "text/plain")}
    resp = await async_client.post("/api/v1/ingest/file", files=files)
    assert resp.status_code == 200
    res = resp.json()
    assert res["success"] is True
    assert res["accepted_count"] == 2


@pytest.mark.asyncio
async def test_events_query_and_metrics_endpoints(async_client: AsyncClient):
    # Ingest event
    payload = {
        "source_type": "auto",
        "logs": [
            '192.0.2.1 - - [25/Oct/2026:10:00:00 +0000] "GET /api/v1/querytest HTTP/1.1" 200 120 "-" "test"'
        ]
    }
    await async_client.post("/api/v1/ingest/raw", json=payload)

    # Query events
    events_resp = await async_client.get("/api/v1/events", params={"path": "/querytest"})
    assert events_resp.status_code == 200
    ev_data = events_resp.json()
    assert ev_data["returned_count"] >= 1
    assert any(e["path"] == "/api/v1/querytest" for e in ev_data["events"])

    # Query metrics
    metrics_resp = await async_client.get("/api/v1/metrics/traffic")
    assert metrics_resp.status_code == 200
    m = metrics_resp.json()
    assert m["total_requests"] >= 1
