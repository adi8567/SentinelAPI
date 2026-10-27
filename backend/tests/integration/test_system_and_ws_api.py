"""Integration tests for System Telemetry, Security Headers, and WebSocket streaming."""

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient
from backend.app.main import app
from backend.app.services.streaming.websocket_manager import ws_manager


@pytest.mark.asyncio
async def test_system_status_endpoint(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert "version" in data
    assert "storage" in data
    assert "pipeline" in data
    assert "detection_engine" in data
    assert "policy_engine" in data
    assert "websockets" in data


@pytest.mark.asyncio
async def test_security_headers_enforced(async_client: AsyncClient):
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200

    # Assert enterprise security headers
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age=31536000" in resp.headers.get("Strict-Transport-Security", "")
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in resp.headers.get("Content-Security-Policy", "")


def test_websocket_connection_and_broadcast():
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/live-traffic") as websocket:
        # Initial handshake
        greeting = websocket.receive_json()
        assert greeting["type"] == "connection_established"
        assert greeting["topic"] == "traffic"

        # Ping-pong
        websocket.send_text("ping")
        resp = websocket.receive_text()
        assert resp == "pong"
