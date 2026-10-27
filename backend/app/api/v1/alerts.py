"""SentinelAPI Security Alerts and Incidents REST Endpoints.

Provides alert queue management, analyst triage, notes, mitigation, and false-positive marking.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from backend.app.api.deps import CurrentPrincipal
from backend.app.schemas.alert import (
    AlertMitigateRequest,
    AlertRecord,
    AlertStatus,
    AlertUpdate,
)
from backend.app.schemas.anomaly import SeverityLevel
from backend.app.services.alert.alert_service import alert_service

router = APIRouter(prefix="/alerts", tags=["Alerts & Incident Response"])


class FalsePositiveRequest(BaseModel):
    reason: str = Field("Verified benign business activity", description="Rationale for false positive marking")


@router.get("", response_model=List[AlertRecord])
async def list_alerts(
    principal: CurrentPrincipal,
    status_filter: Optional[AlertStatus] = Query(None, alias="status", description="Filter by alert status"),
    severity_filter: Optional[SeverityLevel] = Query(None, alias="severity", description="Filter by severity level"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[AlertRecord]:
    """Retrieves paginated list of security alerts."""
    status_str = status_filter.value if status_filter else None
    sev_str = severity_filter.value if severity_filter else None
    return await alert_service.list_alerts(
        status=status_str,
        severity=sev_str,
        limit=limit,
        offset=offset,
    )


@router.get("/{alert_id}", response_model=AlertRecord)
async def get_alert(
    principal: CurrentPrincipal,
    alert_id: str,
) -> AlertRecord:
    """Retrieves full details for a specific alert."""
    alert = await alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found.",
        )
    return alert


@router.patch("/{alert_id}", response_model=AlertRecord)
async def update_alert(
    principal: CurrentPrincipal,
    alert_id: str,
    req: AlertUpdate,
) -> AlertRecord:
    """Updates alert triage status, assigns an analyst, or adds an investigation note."""
    updated = await alert_service.update_alert(alert_id, req)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found.",
        )
    return updated


@router.post("/{alert_id}/mitigate", response_model=AlertRecord)
async def mitigate_alert(
    principal: CurrentPrincipal,
    alert_id: str,
    req: AlertMitigateRequest,
) -> AlertRecord:
    """Executes a defensive response action (block, quarantine) to mitigate an active alert."""
    mitigated = await alert_service.mitigate_alert(alert_id, req)
    if not mitigated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found.",
        )
    return mitigated


@router.post("/{alert_id}/false-positive", response_model=AlertRecord)
async def mark_alert_false_positive(
    principal: CurrentPrincipal,
    alert_id: str,
    req: FalsePositiveRequest,
) -> AlertRecord:
    """Marks an alert as a false positive with analyst explanation."""
    res = await alert_service.mark_false_positive(alert_id, req.reason)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found.",
        )
    return res
