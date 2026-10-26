"""Integration Tests for Inventory API Endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_inventory_api_flow(async_client: AsyncClient):
    # 1. Ingest batch with dynamic paths
    payload = {
        "source_type": "auto",
        "logs": [
            '198.51.100.42 - - [25/Oct/2026:10:00:01 +0000] "GET /api/v1/customers/cst_101 HTTP/1.1" 200 48 "-" "curl/7.88.1"',
            '198.51.100.42 - - [25/Oct/2026:10:00:02 +0000] "GET /api/v1/customers/cst_102 HTTP/1.1" 200 48 "-" "curl/7.88.1"',
            '198.51.100.88 - - [25/Oct/2026:10:00:03 +0000] "POST /api/v1/admin/purge HTTP/1.1" 403 12 "-" "python/3.11"',
        ]
    }
    ingest_resp = await async_client.post("/api/v1/ingest/raw", json=payload)
    assert ingest_resp.status_code == 200

    # 2. Query endpoints
    eps_resp = await async_client.get("/api/v1/inventory/endpoints")
    assert eps_resp.status_code == 200
    eps = eps_resp.json()
    assert len(eps) >= 2

    # Verify template consolidation
    cust_ep = next((e for e in eps if "/customers/{id}" in e["path_template"]), None)
    assert cust_ep is not None
    assert cust_ep["call_count"] == 2
    assert cust_ep["http_method"] == "GET"

    # Verify admin endpoint risk classification
    admin_ep = next((e for e in eps if "/admin/purge" in e["path_template"]), None)
    assert admin_ep is not None
    assert admin_ep["risk_level"] == "critical"

    # 3. Query single endpoint detail
    detail_resp = await async_client.get(f"/api/v1/inventory/endpoints/{cust_ep['endpoint_id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["endpoint_id"] == cust_ep["endpoint_id"]

    # 4. Query clients
    clients_resp = await async_client.get("/api/v1/inventory/clients")
    assert clients_resp.status_code == 200
    clients = clients_resp.json()
    assert len(clients) >= 2

    # 5. Query inventory summary
    summary_resp = await async_client.get("/api/v1/inventory/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_endpoints"] >= 2
    assert summary["total_clients"] >= 2
