"""SentinelAPI API Inventory & Asset Discovery Endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.api.deps import CurrentPrincipal
from backend.app.schemas.inventory import (
    ClientRecord,
    EndpointRecord,
    InventorySummary,
    SessionRecord,
)
from backend.app.services.inventory.inventory_service import inventory_service

router = APIRouter(prefix="/inventory", tags=["API Inventory & Catalog"])


@router.get("/endpoints", response_model=List[EndpointRecord])
async def list_endpoints(
    principal: CurrentPrincipal,
    method: Optional[str] = Query(None, description="Filter by HTTP method (GET, POST, etc.)"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (low, medium, high, critical)"),
    search: Optional[str] = Query(None, description="Search path template"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[EndpointRecord]:
    """Lists all discovered API endpoints with parameter schemas, risk levels, and call stats."""
    return inventory_service.list_endpoints(
        method=method,
        risk_level=risk_level,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/endpoints/{endpoint_id}", response_model=EndpointRecord)
async def get_endpoint_detail(
    endpoint_id: str,
    principal: CurrentPrincipal,
) -> EndpointRecord:
    """Retrieves deep details for a single discovered API endpoint."""
    ep = inventory_service.get_endpoint(endpoint_id)
    if not ep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint with ID '{endpoint_id}' not found in inventory.",
        )
    return ep


@router.get("/clients", response_model=List[ClientRecord])
async def list_clients(
    principal: CurrentPrincipal,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[ClientRecord]:
    """Lists discovered API consumers, callers, and identities."""
    return inventory_service.list_clients(limit=limit, offset=offset)


@router.get("/clients/{client_id}", response_model=ClientRecord)
async def get_client_detail(
    client_id: str,
    principal: CurrentPrincipal,
) -> ClientRecord:
    """Retrieves identity, error profile, and reputation for an API consumer."""
    cl = inventory_service.get_client(client_id)
    if not cl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client '{client_id}' not found.",
        )
    return cl


@router.get("/sessions", response_model=List[SessionRecord])
async def list_sessions(
    principal: CurrentPrincipal,
    limit: int = Query(50, ge=1, le=200),
) -> List[SessionRecord]:
    """Lists active and recent behavioral sessions with endpoint call sequences."""
    return inventory_service.list_sessions(limit=limit)


@router.get("/summary", response_model=InventorySummary)
async def get_inventory_summary(
    principal: CurrentPrincipal,
) -> InventorySummary:
    """Returns aggregated inventory catalog metrics."""
    return inventory_service.get_summary()


@router.post("/discover")
async def trigger_inventory_discovery(
    principal: CurrentPrincipal,
) -> Dict[str, Any]:
    """Triggers an asset discovery scan over historical stored traffic."""
    return await inventory_service.discover_from_history()
