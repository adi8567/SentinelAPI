"""Integration tests for Dashboard Aggregation and Visualization APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_overview_endpoint(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_requests" in data
    assert "total_anomalies" in data
    assert "anomaly_rate_percent" in data
    assert "avg_latency_ms" in data
    assert "system_health" in data


@pytest.mark.asyncio
async def test_dashboard_visualizations_endpoints(async_client: AsyncClient):
    # 1. Traffic time series
    traffic_resp = await async_client.get("/api/v1/dashboard/traffic-timeseries?limit=30")
    assert traffic_resp.status_code == 200
    points = traffic_resp.json()
    assert isinstance(points, list)

    # 2. Anomalies time series
    anom_resp = await async_client.get("/api/v1/dashboard/anomalies-timeseries?limit=30")
    assert anom_resp.status_code == 200
    assert isinstance(anom_resp.json(), list)

    # 3. Risk score distribution
    risk_resp = await async_client.get("/api/v1/dashboard/risk-distribution")
    assert risk_resp.status_code == 200
    risk_data = risk_resp.json()
    assert "histogram" in risk_data
    assert "p50" in risk_data
    assert "p95" in risk_data
    assert "0-20" in risk_data["histogram"]

    # 4. Top endpoints
    top_resp = await async_client.get("/api/v1/dashboard/top-endpoints?limit=5")
    assert top_resp.status_code == 200
    assert isinstance(top_resp.json(), list)

    # 5. Endpoint health matrix
    health_resp = await async_client.get("/api/v1/dashboard/endpoint-health")
    assert health_resp.status_code == 200
    assert isinstance(health_resp.json(), list)

    # 6. Geo distribution
    geo_resp = await async_client.get("/api/v1/dashboard/geo-distribution")
    assert geo_resp.status_code == 200
    geo_data = geo_resp.json()
    assert len(geo_data) >= 1

    # 7. Actions breakdown
    actions_resp = await async_client.get("/api/v1/dashboard/actions-breakdown")
    assert actions_resp.status_code == 200
    act_data = actions_resp.json()
    assert "actions" in act_data
    assert "active_bans_count" in act_data
