"""Unit Tests for Online and Batch Baseline Learning Engines."""

from datetime import datetime, timezone
import math
import numpy as np
import pytest
from backend.app.schemas.events import ApiEvent, LogSource
from backend.app.services.baseline.batch_learner import BatchBaselineLearner
from backend.app.services.baseline.online_updater import OnlineBaselineUpdater, WelfordAccumulator
from backend.app.services.storage.duckdb_client import DuckDBStorageRepository


def test_welford_accumulator():
    acc = WelfordAccumulator()
    data = [10.0, 20.0, 30.0, 40.0, 50.0]
    for x in data:
        acc.update(x)

    assert acc.count == 5
    assert acc.mean == pytest.approx(np.mean(data), 0.001)
    assert acc.variance == pytest.approx(np.var(data, ddof=0), 0.001)
    assert acc.std_dev == pytest.approx(np.std(data, ddof=0), 0.001)


def test_online_baseline_updater():
    updater = OnlineBaselineUpdater()
    now = datetime.now(timezone.utc)

    for i in range(10):
        ev = ApiEvent(
            source_type=LogSource.GENERIC_HTTP,
            http_method="GET",
            path=f"/api/v1/orders/{i}",
            raw_path=f"/api/v1/orders/{i}",
            status_code=200 if i < 8 else 500,
            latency_ms=20.0 + i * 5.0,
            client_ip="198.51.100.1",
            request_size_bytes=100 + i * 10,
            response_size_bytes=500 + i * 20,
            timestamp=now,
        )
        base = updater.observe_event(ev)

    assert base.sample_size == 10
    assert base.latency_mean > 20.0
    assert base.latency_std > 0.0
    assert "200" in base.status_code_distribution
    assert "500" in base.status_code_distribution
    assert base.status_code_distribution["200"] == 0.8
    assert base.status_code_distribution["500"] == 0.2


@pytest.mark.asyncio
async def test_batch_baseline_learner():
    repo = DuckDBStorageRepository(db_path=":memory:")
    await repo.initialize()

    now = datetime.now(timezone.utc)
    events = []
    for i in range(25):
        events.append(
            ApiEvent(
                source_type=LogSource.NGINX,
                http_method="POST",
                path="/api/v1/checkout",
                raw_path="/api/v1/checkout",
                status_code=201 if i < 20 else 400,
                latency_ms=50.0 + (i * 2.0),
                client_ip="198.51.100.5",
                request_size_bytes=300,
                response_size_bytes=800,
                timestamp=now,
            )
        )

    await repo.store_events(events)

    learner = BatchBaselineLearner(storage=repo)
    result = await learner.compute_all_baselines()

    assert result.success is True
    assert result.endpoints_computed == 1
    assert result.clients_computed == 1
    assert result.total_events_analyzed == 25

    ep_baseline = learner.get_all_endpoint_baselines()[0]
    assert ep_baseline.sample_size == 25
    assert ep_baseline.latency_p50 > 50.0
    assert ep_baseline.latency_p95 > ep_baseline.latency_p50
    assert ep_baseline.status_code_distribution["201"] == 0.8
    assert ep_baseline.status_code_distribution["400"] == 0.2

    client_baseline = learner.get_client_baseline("198.51.100.5")
    assert client_baseline is not None
    assert client_baseline.sample_size == 25
    assert client_baseline.error_ratio == pytest.approx(0.2, 0.01)

    await repo.close()
