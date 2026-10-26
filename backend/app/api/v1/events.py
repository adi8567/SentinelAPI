"""SentinelAPI Query and Event Inspection Endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from backend.app.api.deps import CurrentPrincipal, StorageDep

router = APIRouter(prefix="", tags=["Events & Traffic Query"])


@router.get("/events")
async def list_events(
    storage: StorageDep,
    principal: CurrentPrincipal,
    start_time: Optional[datetime] = Query(None, description="Start timestamp filter (ISO8601)"),
    end_time: Optional[datetime] = Query(None, description="End timestamp filter (ISO8601)"),
    http_method: Optional[str] = Query(None, description="Filter by HTTP method (GET, POST, etc.)"),
    path: Optional[str] = Query(None, description="Filter by path substring"),
    status_code: Optional[int] = Query(None, description="Filter by HTTP status code"),
    client_ip: Optional[str] = Query(None, description="Filter by client IP"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Queries stored normalized ApiEvents from the analytical storage engine."""
    events = await storage.query_events(
        start_time=start_time,
        end_time=end_time,
        http_method=http_method,
        path=path,
        status_code=status_code,
        client_ip=client_ip,
        limit=limit,
        offset=offset,
    )
    total_count = await storage.get_total_events_count()

    return {
        "total_count": total_count,
        "returned_count": len(events),
        "limit": limit,
        "offset": offset,
        "events": events,
    }


@router.get("/metrics/traffic")
async def get_traffic_metrics(
    storage: StorageDep,
    principal: CurrentPrincipal,
) -> Dict[str, Any]:
    """Returns aggregated traffic statistics (p50, p95, p99 latency, status distribution, top endpoints)."""
    return await storage.get_traffic_metrics()
