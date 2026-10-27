"""Integration tests for Observability, Prometheus Metrics, and Tracing Headers."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(async_client: AsyncClient):
    # Perform an API call first to generate metrics
    await async_client.get("/api/v1/health")

    # Scrape Prometheus metrics
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")

    body = response.text
    assert "sentinel_http_requests_total" in body
    assert "sentinel_http_request_duration_seconds" in body


@pytest.mark.asyncio
async def test_traceparent_and_security_headers(async_client: AsyncClient):
    # Send custom incoming traceparent
    incoming_tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    response = await async_client.get(
        "/api/v1/health",
        headers={"traceparent": incoming_tp, "X-Request-ID": "test-req-corr-123"},
    )
    assert response.status_code == 200

    # Verify headers
    headers = response.headers
    assert headers.get("X-Request-ID") == "test-req-corr-123"
    assert "X-Response-Time-Ms" in headers
    assert "traceparent" in headers

    # Verify propagated trace_id matches incoming parent trace_id
    resp_tp = headers["traceparent"]
    assert resp_tp.startswith("00-4bf92f3577b34da6a3ce929d0e0e4736-")

    # Verify security hardening headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Strict-Transport-Security" in headers
