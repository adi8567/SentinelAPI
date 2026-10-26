"""Integration Tests Verifying Real Dataset Ingestion."""

from pathlib import Path
import pytest
from httpx import AsyncClient
from backend.app.schemas.events import LogSource
from backend.app.services.ingestion.pipeline import IngestionPipeline
from backend.app.services.storage.duckdb_client import DuckDBStorageRepository
from backend.app.services.streaming.kafka_client import ResilientStreamBuffer


@pytest.mark.asyncio
async def test_all_real_datasets_ingest_without_errors():
    datasets_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "real_datasets"
    assert datasets_dir.exists(), f"Datasets directory {datasets_dir} must exist."

    repo = DuckDBStorageRepository(db_path=":memory:")
    await repo.initialize()

    class MockStreamer:
        def __init__(self):
            self.events = []
        async def produce_batch(self, events):
            self.events.extend(events)
            return len(events)
        async def produce_event(self, event, topic=""):
            self.events.append(event)
            return True
        def get_stats(self):
            return {"buffer_stats": {"buffered_events": len(self.events)}}

    mock_stream = MockStreamer()
    pipeline = IngestionPipeline(storage=repo, streaming=mock_stream)

    expected_files = [
        ("nginx_access.log", 20, "nginx"),
        ("envoy_access.json", 10, "envoy"),
        ("kong_gateway.json", 5, "kong"),
        ("aws_api_gateway.json", 5, "aws_apigw"),
        ("azure_apim.json", 5, "azure_apim"),
        ("gcp_endpoints.json", 5, "gcp_endpoints"),
        ("otel_traces.json", 5, "opentelemetry"),
        ("real_api_sec_attacks.log", 15, "nginx"),
    ]

    total_expected = sum(count for _, count, _ in expected_files)
    total_accepted = 0

    for filename, count, expected_source in expected_files:
        file_path = datasets_dir / filename
        assert file_path.exists(), f"File {file_path} must exist."

        with open(file_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        assert len(lines) == count, f"File {filename} has {len(lines)} lines, expected {count}."

        result = await pipeline.ingest_raw_batch(
            raw_lines=lines,
            source_type=LogSource.AUTO,
            gateway_id=f"test-{filename}",
            store_raw=True,
        )

        assert result.success is True, f"Failed ingestion for {filename}: {result.parse_errors}"
        assert result.accepted_count == count, f"{filename}: accepted {result.accepted_count} != {count}"
        assert result.rejected_count == 0, f"{filename} had {result.rejected_count} errors: {result.parse_errors}"
        assert result.source_detected == expected_source
        total_accepted += result.accepted_count

    assert total_accepted == total_expected == 70

    # Verify DuckDB storage content
    db_count = await repo.get_total_events_count()
    assert db_count == 70

    # Verify traffic metrics computation
    metrics = await repo.get_traffic_metrics()
    assert metrics["total_requests"] == 70
    assert metrics["avg_latency_ms"] > 0
    assert metrics["p95_latency_ms"] > metrics["p50_latency_ms"]
    assert "200" in metrics["status_breakdown"]
    assert "403" in metrics["status_breakdown"]
    assert "401" in metrics["status_breakdown"]

    # Verify streaming buffer received all 70 events
    assert len(mock_stream.events) == 70

    await repo.close()
