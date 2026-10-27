"""Integration tests for Forensic Investigation & Tracing APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_investigation_client_and_endpoint(async_client: AsyncClient):
    # Ingest a real request
    payload = {
        "source_type": "auto",
        "logs": [
            '198.51.100.95 - - [25/Oct/2026:11:00:20 +0000] "GET /api/v1/catalog/items/456 HTTP/1.1" 200 450 "-" "Mozilla/5.0"',
        ]
    }
    await async_client.post("/api/v1/ingest/raw", json=payload)

    # 1. Investigate client
    client_resp = await async_client.get("/api/v1/investigation/client/198.51.100.95")
    assert client_resp.status_code == 200
    client_data = client_resp.json()
    assert client_data["client_ip"] == "198.51.100.95"
    assert "reputation_score" in client_data
    assert "total_requests" in client_data
    assert "is_banned" in client_data

    # 2. Investigate endpoint
    inv_resp = await async_client.get("/api/v1/inventory/endpoints")
    endpoints = inv_resp.json()
    assert len(endpoints) >= 1
    test_ep_id = endpoints[0]["endpoint_id"]

    ep_resp = await async_client.get(f"/api/v1/investigation/endpoint/{test_ep_id}")
    assert ep_resp.status_code == 200
    ep_data = ep_resp.json()
    assert ep_data["endpoint_id"] == test_ep_id
    assert "path_template" in ep_data
    assert "risk_level" in ep_data
    assert "status_distribution" in ep_data

    # 3. Sequence flow graph
    seq_resp = await async_client.get("/api/v1/investigation/sequences")
    assert seq_resp.status_code == 200
    seq_data = seq_resp.json()
    assert "nodes" in seq_data
    assert "links" in seq_data


@pytest.mark.asyncio
async def test_investigation_trace_event(async_client: AsyncClient):
    # Ingest event and fetch its event_id
    payload = {
        "source_type": "auto",
        "logs": [
            '198.51.100.44 - - [25/Oct/2026:11:00:15 +0000] "GET /api/v1/orders/789 HTTP/1.1" 200 350 "-" "curl/7.81.0"',
        ]
    }
    await async_client.post("/api/v1/ingest/raw", json=payload)

    events_resp = await async_client.get("/api/v1/events?limit=1")
    events_data = events_resp.json()
    assert events_data.get("returned_count", 0) >= 1
    event_id = events_data["events"][0]["event_id"]

    # Forensic trace
    trace_resp = await async_client.get(f"/api/v1/investigation/trace/{event_id}")
    assert trace_resp.status_code == 200
    trace_data = trace_resp.json()
    assert trace_data["event_id"] == event_id
    assert "normalized_event" in trace_data
    assert "client_reputation" in trace_data
