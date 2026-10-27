"""Integration Tests Verifying Anomaly Detection on Real Attack Traffic."""

from pathlib import Path
import pytest
from backend.app.schemas.events import LogSource
from backend.app.services.detection.engine import anomaly_engine
from backend.app.services.ingestion.pipeline import IngestionPipeline
from backend.app.services.storage.duckdb_client import DuckDBStorageRepository


@pytest.mark.asyncio
async def test_real_attack_dataset_detection():
    data_file = Path(__file__).resolve().parent.parent.parent.parent / "data" / "real_datasets" / "real_api_sec_attacks.log"
    assert data_file.exists()

    repo = DuckDBStorageRepository(db_path=":memory:")
    await repo.initialize()

    class MockStreamer:
        async def produce_batch(self, events): return len(events)
        async def produce_event(self, event, topic=""): return True
        def get_stats(self): return {"buffer_stats": {"buffered_events": 0}}

    pipeline = IngestionPipeline(storage=repo, streaming=MockStreamer())

    with open(data_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 15

    # Ingest the authentic OWASP API attack dataset
    result = await pipeline.ingest_raw_batch(
        raw_lines=lines,
        source_type=LogSource.AUTO,
        gateway_id="sec-test-gw",
        store_raw=True,
    )
    assert result.success is True
    assert result.accepted_count == 15

    # Check anomalies flagged by the engine
    anomalies = anomaly_engine.list_anomalies(min_risk_score=50.0)
    assert len(anomalies) >= 4, f"Expected at least 4 attacks detected, got {len(anomalies)}"

    # 1. SQL Injection detected
    sqli_anoms = [a for a in anomalies if any("SQL Injection" in f for f in a.contributing_factors)]
    assert len(sqli_anoms) >= 1
    assert sqli_anoms[0].risk_score >= 80.0

    # 2. Path Traversal detected
    traversal_anoms = [a for a in anomalies if any("traversal" in f.lower() for f in a.contributing_factors)]
    assert len(traversal_anoms) >= 1

    # 3. BOLA / IDOR detected
    bola_anoms = [a for a in anomalies if any("BOLA" in f for f in a.contributing_factors)]
    assert len(bola_anoms) >= 1

    # 4. Credential Stuffing detected
    auth_anoms = [a for a in anomalies if any("Credential Stuffing" in f or "Brute Force" in f for f in a.contributing_factors)]
    assert len(auth_anoms) >= 1

    await repo.close()
