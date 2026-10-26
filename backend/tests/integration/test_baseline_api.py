"""Integration Tests for Baseline Learning API Endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_baseline_api_flow(async_client: AsyncClient):
    # 1. Ingest real log batch
    payload = {
        "source_type": "auto",
        "logs": [
            '198.51.100.10 - - [25/Oct/2026:10:00:01 +0000] "GET /api/v1/billing/plans HTTP/1.1" 200 120 "-" "curl/7.88.1" 0.020 0.018 100',
            '198.51.100.10 - - [25/Oct/2026:10:00:02 +0000] "GET /api/v1/billing/plans HTTP/1.1" 200 120 "-" "curl/7.88.1" 0.025 0.022 100',
            '198.51.100.10 - - [25/Oct/2026:10:00:03 +0000] "GET /api/v1/billing/plans HTTP/1.1" 200 120 "-" "curl/7.88.1" 0.030 0.028 100',
        ]
    }
    await async_client.post("/api/v1/ingest/raw", json=payload)

    # 2. Trigger batch recomputation
    recomp_resp = await async_client.post("/api/v1/baselines/recompute")
    assert recomp_resp.status_code == 200
    res = recomp_resp.json()
    assert res["success"] is True
    assert res["endpoints_computed"] >= 1

    # 3. Query all baselines
    all_resp = await async_client.get("/api/v1/baselines/endpoints")
    assert all_resp.status_code == 200
    baselines = all_resp.json()
    assert len(baselines) >= 1

    plan_base = baselines[0]
    assert plan_base["sample_size"] >= 3
    assert plan_base["latency_p50"] > 0
    assert "200" in plan_base["status_code_distribution"]

    # 4. Query single endpoint baseline
    single_resp = await async_client.get(f"/api/v1/baselines/endpoints/{plan_base['endpoint_id']}")
    assert single_resp.status_code == 200
    assert single_resp.json()["endpoint_id"] == plan_base["endpoint_id"]
