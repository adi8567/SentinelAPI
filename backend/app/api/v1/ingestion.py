"""SentinelAPI Traffic Ingestion Endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from backend.app.api.deps import CurrentPrincipal, PipelineDep, StorageDep
from backend.app.core.security import Role, require_role
from backend.app.schemas.events import (
    ApiEvent,
    BatchEventsRequest,
    BatchRawLogRequest,
    IngestionResult,
    LogSource,
)
from backend.app.schemas.health import IngestionStatsResponse

router = APIRouter(prefix="/ingest", tags=["Data Ingestion Pipeline"])


@router.post("/raw", response_model=IngestionResult)
async def ingest_raw_logs(
    payload: BatchRawLogRequest,
    pipeline: PipelineDep,
    principal: CurrentPrincipal,
) -> IngestionResult:
    """Consumes and parses a batch of raw API gateway logs (NGINX, Envoy, Kong, AWS, Azure, GCP, OTel).
    Automatically detects the log format or uses the explicitly specified source_type.
    """
    result = await pipeline.ingest_raw_batch(
        raw_lines=payload.logs,
        source_type=payload.source_type,
        gateway_id=payload.gateway_id or "default-gw",
        store_raw=True,
    )
    return result


@router.post("/events", response_model=IngestionResult)
async def ingest_normalized_events(
    payload: BatchEventsRequest,
    pipeline: PipelineDep,
    principal: CurrentPrincipal,
) -> IngestionResult:
    """Directly ingests a batch of pre-normalized ApiEvent records."""
    result = await pipeline.ingest_normalized_events(events=payload.events)
    return result


@router.post("/file", response_model=IngestionResult)
async def ingest_log_file(
    file: UploadFile = File(...),
    pipeline: PipelineDep = None,
    principal: CurrentPrincipal = None,
    source_type: LogSource = Query(default=LogSource.AUTO),
    gateway_id: str = Query(default="file-upload-gw"),
) -> IngestionResult:
    """Accepts a raw log file upload (.log, .txt, .json), parses all lines, and persists events."""
    content_bytes = await file.read()
    try:
        text = content_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not decode uploaded file as UTF-8: {e}",
        )

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty or contains no non-blank lines.",
        )

    result = await pipeline.ingest_raw_batch(
        raw_lines=lines,
        source_type=source_type,
        gateway_id=gateway_id,
        store_raw=True,
    )
    return result


@router.get("/stats", response_model=IngestionStatsResponse)
async def get_ingestion_stats(
    pipeline: PipelineDep,
    principal: CurrentPrincipal,
) -> IngestionStatsResponse:
    """Returns real-time ingestion throughput, byte counts, and source distribution."""
    return IngestionStatsResponse(**pipeline.get_stats())
