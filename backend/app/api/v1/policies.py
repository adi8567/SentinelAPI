"""SentinelAPI Adaptive Protection & Policy REST Endpoints.

Provides administrative APIs for managing declarative security policies, querying
the decision audit trail, managing the active IP blocklist and quarantine, and dry-run testing.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from backend.app.api.deps import CurrentPrincipal
from backend.app.schemas.policy import (
    BlocklistEntry,
    PolicyAction,
    PolicyDecision,
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
    PolicyRule,
    PolicyStats,
    QuarantineEntry,
)
from backend.app.services.policy.actions.ban_manager import ip_ban_manager
from backend.app.services.policy.actions.quarantine_manager import quarantine_manager
from backend.app.services.policy.engine import policy_engine

router = APIRouter(prefix="/policies", tags=["Adaptive Protection & Policies"])


class ManualBanRequest(BaseModel):
    ip: str = Field(..., description="IPv4 or IPv6 address to ban")
    duration_seconds: Optional[int] = Field(3600, description="Ban TTL in seconds (None for permanent)")
    reason: str = Field("Manual operator block", description="Justification for the ban")


class ManualQuarantineRequest(BaseModel):
    client_ip: str
    client_id: Optional[str] = None
    reason: str = "Manual operator quarantine"


@router.get("", response_model=List[PolicyRule])
async def list_policies(
    principal: CurrentPrincipal,
    enabled_only: bool = Query(False, description="Filter to only enabled policies"),
) -> List[PolicyRule]:
    """Retrieves all declarative policy rules ordered by priority."""
    return await policy_engine.get_rules(enabled_only=enabled_only)


@router.post("", response_model=PolicyRule, status_code=status.HTTP_201_CREATED)
async def create_or_update_policy(
    principal: CurrentPrincipal,
    rule: PolicyRule,
) -> PolicyRule:
    """Creates or updates a declarative security policy rule (Policy-as-Code)."""
    return await policy_engine.add_or_update_rule(rule)


@router.get("/decisions", response_model=List[PolicyDecision])
async def list_policy_decisions(
    principal: CurrentPrincipal,
    action: Optional[PolicyAction] = Query(None, description="Filter decisions by action taken"),
    client_ip: Optional[str] = Query(None, description="Filter by client IP"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[PolicyDecision]:
    """Retrieves immutable audit trail of automated adaptive protection decisions."""
    action_str = action.value if action else None
    return await policy_engine.get_decisions(
        action=action_str,
        client_ip=client_ip,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=PolicyStats)
async def get_policy_statistics(
    principal: CurrentPrincipal,
) -> PolicyStats:
    """Returns operational metrics and action breakdown for adaptive protection policies."""
    return await policy_engine.get_stats()


@router.get("/blocklist", response_model=List[BlocklistEntry])
async def get_active_blocklist(
    principal: CurrentPrincipal,
) -> List[BlocklistEntry]:
    """Lists all currently active IP bans and their remaining TTL."""
    return await ip_ban_manager.list_active_bans()


@router.post("/blocklist", response_model=BlocklistEntry, status_code=status.HTTP_201_CREATED)
async def manual_ban_ip(
    principal: CurrentPrincipal,
    req: ManualBanRequest,
) -> BlocklistEntry:
    """Manually places an IP address on the active blocklist."""
    return await ip_ban_manager.ban_ip(
        ip=req.ip,
        duration_seconds=req.duration_seconds,
        reason=req.reason,
        policy_id="operator_manual",
    )


@router.delete("/blocklist/{ip}", status_code=status.HTTP_200_OK)
async def remove_ip_from_blocklist(
    principal: CurrentPrincipal,
    ip: str,
) -> Dict[str, Any]:
    """Manually unbans an IP address."""
    removed = await ip_ban_manager.unban_ip(ip)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IP '{ip}' is not found in active blocklist.",
        )
    return {"status": "success", "unbanned_ip": ip}


@router.get("/quarantine", response_model=List[QuarantineEntry])
async def get_quarantined_clients(
    principal: CurrentPrincipal,
) -> List[QuarantineEntry]:
    """Lists all client identities currently isolated in quarantine."""
    return await quarantine_manager.list_active()


@router.post("/quarantine", response_model=QuarantineEntry, status_code=status.HTTP_201_CREATED)
async def manual_quarantine_client(
    principal: CurrentPrincipal,
    req: ManualQuarantineRequest,
) -> QuarantineEntry:
    """Manually places a client IP in quarantine."""
    return await quarantine_manager.quarantine(
        client_ip=req.client_ip,
        client_id=req.client_id,
        reason=req.reason,
        policy_id="operator_manual",
    )


@router.delete("/quarantine/{client_ip}", status_code=status.HTTP_200_OK)
async def release_from_quarantine(
    principal: CurrentPrincipal,
    client_ip: str,
) -> Dict[str, Any]:
    """Releases a client IP from quarantine."""
    released = await quarantine_manager.release(client_ip)
    if not released:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IP '{client_ip}' is not found in active quarantine.",
        )
    return {"status": "success", "released_ip": client_ip}


@router.post("/evaluate", response_model=PolicyEvaluationResponse)
async def test_policy_evaluation(
    principal: CurrentPrincipal,
    req: PolicyEvaluationRequest,
) -> PolicyEvaluationResponse:
    """Dry-run test policy evaluation against simulated or historic parameters without side effects."""
    return await policy_engine.dry_run_evaluate(req)


@router.get("/{policy_id}", response_model=PolicyRule)
async def get_policy(
    principal: CurrentPrincipal,
    policy_id: str,
) -> PolicyRule:
    """Retrieves a single policy rule by its ID."""
    rules = await policy_engine.get_rules()
    for r in rules:
        if r.policy_id == policy_id:
            return r
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Policy '{policy_id}' not found.",
    )


@router.delete("/{policy_id}", status_code=status.HTTP_200_OK)
async def delete_policy(
    principal: CurrentPrincipal,
    policy_id: str,
) -> Dict[str, Any]:
    """Deletes or deactivates a policy rule."""
    deleted = await policy_engine.delete_rule(policy_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy '{policy_id}' not found.",
        )
    return {"status": "success", "deleted_policy_id": policy_id}
