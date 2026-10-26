"""Unit Tests for Analytical Storage Engine."""

from datetime import datetime, timezone
import pytest
from backend.app.schemas.events import ApiEvent, LogSource
from backend.app.services.storage.duckdb_client import DuckDBStorageRepository


@pytest.mark.asyncio
async def test_duckdb_storage_lifecycle_and_aggregates():
    repo = DuckDBStorageRepository(db_path=":memory:")
    await repo.initialize()

    # Empty table check
    count = await repo.get_total_events_count()
    assert count == 0

    now = datetime.now(timezone.utc)
    events = [
        ApiEvent(
            source_type=LogSource.NGINX,
            http_method="GET",
            path="/api/v1/orders",
            raw_path="/api/v1/orders",
            status_code=200,
            latency_ms=25.0,
            client_ip="198.51.100.1",
            timestamp=now,
        ),
        ApiEvent(
            source_type=LogSource.ENVOY,
            http_method="POST",
            path="/api/v1/checkout",
            raw_path="/api/v1/checkout",
            status_code=201,
            latency_ms=105.0,
            client_ip="203.0.113.2",
            timestamp=now,
        ),
        ApiEvent(
            source_type=LogSource.KONG,
            http_method="GET",
            path="/api/v1/orders",
            raw_path="/api/v1/orders",
            status_code=500,
            latency_ms=45.0,
            client_ip="198.51.100.1",
            timestamp=now,
        ),
    ]

    inserted = await repo.store_events(events)
    assert inserted == 3

    total_count = await repo.get_total_events_count()
    assert total_count == 3

    # Query with filtering
    orders_events = await repo.query_events(path="/orders")
    assert len(orders_events) == 2

    post_events = await repo.query_events(http_method="POST")
    assert len(post_events) == 1
    assert post_events[0]["status_code"] == 201

    # Check analytical metrics calculation
    metrics = await repo.get_traffic_metrics()
    assert metrics["total_requests"] == 3
    assert metrics["avg_latency_ms"] == pytest.approx(58.33, 0.1)
    assert metrics["status_breakdown"] == {"200": 1, "201": 1, "500": 1}
    assert metrics["methods_breakdown"] == {"GET": 2, "POST": 1}

    # Health check
    health = await repo.health_check()
    assert health["status"] == "healthy"

    await repo.close()
