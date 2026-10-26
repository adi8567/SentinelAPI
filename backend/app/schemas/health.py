"""SentinelAPI Health and Diagnostic Schemas."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ServiceComponentHealth(BaseModel):
    name: str
    status: str  # "healthy", "degraded", "down"
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str  # "ok", "degraded", "error"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str
    environment: str
    components: Dict[str, ServiceComponentHealth] = Field(default_factory=dict)


class IngestionStatsResponse(BaseModel):
    total_events_ingested: int
    total_raw_logs_ingested: int
    events_per_second: float
    total_bytes_processed: int
    sources_breakdown: Dict[str, int]
    error_count: int
    uptime_seconds: float
    streaming_buffer_size: int
    storage_engine: str
