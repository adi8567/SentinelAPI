"""SentinelAPI Ingestion Pipeline Orchestrator.

Coordinates parsing, normalization, audit logging, streaming to Kafka,
and persistence to analytical storage.
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from backend.app.core.config import settings
from backend.app.schemas.events import (
    ApiEvent,
    IngestionResult,
    LogSource,
    ParseErrorDetail,
)
from backend.app.services.baseline.online_updater import online_baseline_updater
from backend.app.services.detection.engine import anomaly_engine
from backend.app.services.ingestion.auto_detector import parser_registry
from backend.app.services.inventory.inventory_service import inventory_service
from backend.app.services.storage.factory import get_storage
from backend.app.services.storage.repository import IStorageRepository
from backend.app.services.streaming.kafka_client import stream_producer
from backend.app.services.streaming.producer import IStreamingProducer

logger = logging.getLogger("sentinelapi.pipeline")


class IngestionPipeline:
    """End-to-end API Traffic Ingestion Pipeline."""

    def __init__(
        self,
        storage: Optional[IStorageRepository] = None,
        streaming: Optional[IStreamingProducer] = None,
    ):
        self._storage = storage
        self._streaming = streaming or stream_producer
        self._start_time = datetime.now(timezone.utc)
        self._total_events_ingested: int = 0
        self._total_raw_logs_ingested: int = 0
        self._total_bytes_processed: int = 0
        self._total_errors: int = 0
        self._sources_breakdown: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def _get_storage(self) -> IStorageRepository:
        if self._storage is not None:
            return self._storage
        return await get_storage()

    async def ingest_raw_batch(
        self,
        raw_lines: List[str],
        source_type: LogSource = LogSource.AUTO,
        gateway_id: str = "default-gw",
        store_raw: bool = True,
    ) -> IngestionResult:
        """Parses, streams, and stores a batch of raw log lines."""
        start_ts = time.perf_counter()
        if not raw_lines:
            return IngestionResult(
                success=True,
                total_received=0,
                accepted_count=0,
                rejected_count=0,
                processing_time_ms=0.0,
            )

        storage = await self._get_storage()

        # 1. Parse lines with automatic or requested format
        events, errors, detected_source = parser_registry.parse_with_detection(
            raw_lines, gateway_id=gateway_id, forced_source=source_type
        )

        error_details = [
            ParseErrorDetail(index=idx, line_snippet=snippet, error=err)
            for idx, snippet, err in errors
        ]

        if not events:
            elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
            return IngestionResult(
                success=False,
                total_received=len(raw_lines),
                accepted_count=0,
                rejected_count=len(errors),
                processing_time_ms=round(elapsed_ms, 2),
                source_detected=detected_source,
                parse_errors=error_details,
            )

        # 2. Store raw audit entries if enabled
        if store_raw:
            for line in raw_lines:
                if line.strip():
                    await storage.store_raw_log(line, detected_source, gateway_id)

        # 3. Stream normalized events to Kafka
        await self._streaming.produce_batch(events)

        # 4. Store normalized events in analytical storage
        stored_count = await storage.store_events(events)

        # 5. Continuous Online Inventory Discovery & Baseline Tracking
        await inventory_service.process_batch(events)
        for ev in events:
            online_baseline_updater.observe_event(ev)
            await anomaly_engine.process_and_persist(ev)

        # 6. Update metrics
        raw_bytes = sum(len(line.encode("utf-8")) for line in raw_lines)
        async with self._lock:
            self._total_events_ingested += stored_count
            self._total_raw_logs_ingested += len(raw_lines)
            self._total_bytes_processed += raw_bytes
            self._total_errors += len(errors)
            self._sources_breakdown[detected_source] = (
                self._sources_breakdown.get(detected_source, 0) + stored_count
            )

        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0

        return IngestionResult(
            success=True,
            total_received=len(raw_lines),
            accepted_count=stored_count,
            rejected_count=len(errors),
            processing_time_ms=round(elapsed_ms, 2),
            source_detected=detected_source,
            parse_errors=error_details,
        )

    async def ingest_normalized_events(
        self,
        events: List[ApiEvent],
    ) -> IngestionResult:
        """Streams and persists already-normalized ApiEvents."""
        start_ts = time.perf_counter()
        if not events:
            return IngestionResult(
                success=True,
                total_received=0,
                accepted_count=0,
                rejected_count=0,
                processing_time_ms=0.0,
            )

        storage = await self._get_storage()

        # 1. Stream to Kafka
        await self._streaming.produce_batch(events)

        # 2. Store in database
        stored_count = await storage.store_events(events)

        # 3. Continuous Online Inventory Discovery & Baseline Tracking
        await inventory_service.process_batch(events)
        for ev in events:
            online_baseline_updater.observe_event(ev)
            await anomaly_engine.process_and_persist(ev)

        # 4. Update metrics
        async with self._lock:
            self._total_events_ingested += stored_count
            for e in events:
                src = e.source_type.value
                self._sources_breakdown[src] = self._sources_breakdown.get(src, 0) + 1

        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
        return IngestionResult(
            success=True,
            total_received=len(events),
            accepted_count=stored_count,
            rejected_count=0,
            processing_time_ms=round(elapsed_ms, 2),
            source_detected="normalized_direct",
        )

    def get_stats(self) -> Dict[str, Any]:
        """Calculates live ingestion rate and operational stats."""
        uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        eps = (self._total_events_ingested / uptime) if uptime > 0 else 0.0

        return {
            "total_events_ingested": self._total_events_ingested,
            "total_raw_logs_ingested": self._total_raw_logs_ingested,
            "events_per_second": round(eps, 2),
            "total_bytes_processed": self._total_bytes_processed,
            "sources_breakdown": dict(self._sources_breakdown),
            "error_count": self._total_errors,
            "uptime_seconds": round(uptime, 2),
            "streaming_buffer_size": self._streaming.get_stats().get("buffer_stats", {}).get("buffered_events", 0),
            "storage_engine": settings.STORAGE_BACKEND.value,
        }


# Global pipeline singleton
ingestion_pipeline = IngestionPipeline()
