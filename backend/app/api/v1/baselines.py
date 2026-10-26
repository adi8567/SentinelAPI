"""SentinelAPI Behavioral Baseline Query and Management Endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.api.deps import CurrentPrincipal
from backend.app.schemas.baseline import (
    ClientBaseline,
    EndpointBaseline,
    RecomputeBaselinesResult,
)
from backend.app.services.baseline.batch_learner import batch_baseline_learner
from backend.app.services.baseline.online_updater import online_baseline_updater

router = APIRouter(prefix="/baselines", tags=["Behavioral Baselines"])


@router.get("/endpoints", response_model=List[EndpointBaseline])
async def list_endpoint_baselines(
    principal: CurrentPrincipal,
) -> List[EndpointBaseline]:
    """Returns all computed endpoint behavioral baselines."""
    # Merge batch baselines with real-time online updater
    batch_baselines = {b.endpoint_id: b for b in batch_baseline_learner.get_all_endpoint_baselines()}
    for b in online_baseline_updater.get_all_baselines():
        if b.endpoint_id not in batch_baselines:
            batch_baselines[b.endpoint_id] = b
    return list(batch_baselines.values())


@router.get("/endpoints/{endpoint_id}", response_model=EndpointBaseline)
async def get_endpoint_baseline(
    endpoint_id: str,
    principal: CurrentPrincipal,
) -> EndpointBaseline:
    """Returns the statistical baseline for an endpoint (quantiles, payload size, seasonality)."""
    # Prefer batch baseline, fall back to streaming online baseline
    baseline = batch_baseline_learner.get_endpoint_baseline(endpoint_id)
    if not baseline:
        baseline = online_baseline_updater.get_baseline(endpoint_id)

    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No baseline computed for endpoint ID '{endpoint_id}'.",
        )
    return baseline


@router.get("/clients/{client_id}", response_model=ClientBaseline)
async def get_client_baseline(
    client_id: str,
    principal: CurrentPrincipal,
) -> ClientBaseline:
    """Returns behavioral baseline profile for an API client/identity."""
    baseline = batch_baseline_learner.get_client_baseline(client_id)
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No baseline profile found for client '{client_id}'.",
        )
    return baseline


@router.post("/recompute", response_model=RecomputeBaselinesResult)
async def recompute_baselines(
    principal: CurrentPrincipal,
    limit: int = Query(50000, ge=1, le=200000),
) -> RecomputeBaselinesResult:
    """Triggers batch baseline recomputation across all historical stored events."""
    return await batch_baseline_learner.compute_all_baselines(limit=limit)
