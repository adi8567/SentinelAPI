"""Unit Tests for Inventory Service."""

from datetime import datetime, timezone
import pytest
from backend.app.schemas.events import ApiEvent, AuthType, LogSource
from backend.app.schemas.inventory import ClientType, RiskLevel
from backend.app.services.inventory.inventory_service import InventoryService


@pytest.mark.asyncio
async def test_inventory_discovery_from_events():
    svc = InventoryService()
    now = datetime.now(timezone.utc)

    events = [
        ApiEvent(
            source_type=LogSource.NGINX,
            http_method="GET",
            path="/api/v1/users/1001",
            raw_path="/api/v1/users/1001?expand=details",
            query_params={"expand": "details"},
            status_code=200,
            latency_ms=25.0,
            client_ip="198.51.100.22",
            auth_type=AuthType.BEARER,
            auth_identity="sha256:abcd1234efgh5678",
            timestamp=now,
        ),
        ApiEvent(
            source_type=LogSource.NGINX,
            http_method="GET",
            path="/api/v1/users/1002",
            raw_path="/api/v1/users/1002?expand=details",
            query_params={"expand": "details"},
            status_code=403,
            latency_ms=10.0,
            client_ip="198.51.100.22",
            auth_type=AuthType.BEARER,
            auth_identity="sha256:abcd1234efgh5678",
            timestamp=now,
        ),
    ]

    await svc.process_batch(events)

    # Both concrete paths /users/1001 and /users/1002 must merge into single template /api/v1/users/{id}
    endpoints = svc.list_endpoints()
    assert len(endpoints) == 1
    ep = endpoints[0]
    assert ep.path_template == "/api/v1/users/{id}"
    assert ep.http_method == "GET"
    assert ep.call_count == 2
    assert "200" in ep.status_codes_observed
    assert "403" in ep.status_codes_observed
    assert "expand" in ep.parameters
    assert ep.is_authenticated is True

    # Client Record Verification
    clients = svc.list_clients()
    assert len(clients) == 1
    cl = clients[0]
    assert cl.client_id == "sha256:abcd1234efgh5678"
    assert cl.client_type == ClientType.USER
    assert cl.total_requests == 2
    assert cl.error_count == 1
    assert cl.reputation_score == pytest.approx(65.0, 0.5)

    # Session Record Verification
    sessions = svc.list_sessions()
    assert len(sessions) == 1
    sess = sessions[0]
    assert sess.event_count == 2
    assert len(sess.endpoint_sequence) == 2
    assert sess.endpoint_sequence[0] == "/api/v1/users/{id}"

    # Summary Check
    summary = svc.get_summary()
    assert summary.total_endpoints == 1
    assert summary.total_clients == 1
    assert summary.authenticated_endpoints_count == 1
