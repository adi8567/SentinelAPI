"""SentinelAPI Health & Diagnostics Endpoints."""

from datetime import datetime, timezone
import time
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from backend.app.api.deps import StorageDep, get_storage_repo, get_stream_producer
from backend.app.core.config import settings
from backend.app.schemas.health import HealthResponse, ServiceComponentHealth
from backend.app.services.streaming.kafka_client import KafkaStreamProducer

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health", response_model=HealthResponse)
async def health(
    storage: StorageDep,
    streaming: KafkaStreamProducer = Depends(get_stream_producer),
) -> HealthResponse:
    """Overall system health check inspecting storage and streaming subsystems."""
    start_storage = time.perf_counter()
    storage_health = await storage.health_check()
    storage_lat = round((time.perf_counter() - start_storage) * 1000.0, 2)

    streaming_stats = streaming.get_stats()
    streaming_status = "healthy" if (streaming_stats.get("is_kafka_connected") or streaming_stats.get("backend_active") == "memory_buffer" or streaming_stats.get("backend_active") == "memory_fallback") else "degraded"

    overall_status = "ok"
    if storage_health.get("status") != "healthy":
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        components={
            "storage": ServiceComponentHealth(
                name="TimeSeries Storage",
                status=storage_health.get("status", "unknown"),
                latency_ms=storage_lat,
                details=storage_health,
            ),
            "streaming": ServiceComponentHealth(
                name="Streaming Pipeline",
                status=streaming_status,
                details=streaming_stats,
            ),
        },
    )


@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/ready")
async def readiness(storage: StorageDep):
    """Kubernetes readiness probe."""
    health_info = await storage.health_check()
    if health_info.get("status") == "down":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": "Storage unavailable"},
        )
    return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}
