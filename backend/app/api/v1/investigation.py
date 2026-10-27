"""SentinelAPI Forensic Investigation REST Endpoints.

Provides deep trace inspection, client dossier exploration, endpoint deviation metrics,
and sequence flow graphs for analysts and SOC operators.
"""

from fastapi import APIRouter, HTTPException, status
from backend.app.api.deps import CurrentPrincipal
from backend.app.schemas.investigation import (
    ClientInvestigation,
    EndpointInvestigation,
    EventForensicTrace,
    SequenceFlowGraph,
)
from backend.app.services.investigation.investigation_service import investigation_service

router = APIRouter(prefix="/investigation", tags=["Forensic Investigation & Tracing"])


@router.get("/trace/{event_id}", response_model=EventForensicTrace)
async def trace_event(
    principal: CurrentPrincipal,
    event_id: str,
) -> EventForensicTrace:
    """Retrieves full root-cause forensic correlation for an API interaction."""
    trace = await investigation_service.trace_event(event_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found.",
        )
    return trace


@router.get("/client/{client_ip}", response_model=ClientInvestigation)
async def investigate_client(
    principal: CurrentPrincipal,
    client_ip: str,
) -> ClientInvestigation:
    """Generates a complete behavioral investigation profile for a client IP."""
    return await investigation_service.investigate_client(client_ip)


@router.get("/endpoint/{endpoint_id}", response_model=EndpointInvestigation)
async def investigate_endpoint(
    principal: CurrentPrincipal,
    endpoint_id: str,
) -> EndpointInvestigation:
    """Retrieves forensic deviation and baseline comparison for a specific endpoint."""
    res = await investigation_service.investigate_endpoint(endpoint_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{endpoint_id}' not found in inventory.",
        )
    return res


@router.get("/sequences", response_model=SequenceFlowGraph)
async def get_sequence_flow_graph(
    principal: CurrentPrincipal,
) -> SequenceFlowGraph:
    """Retrieves Markov sequence and session call-chain transition graph for Sankey / flow diagrams."""
    return await investigation_service.get_sequence_flow_graph()
