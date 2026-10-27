"""SentinelAPI Adaptive Protection & Policy Schemas.

Data models for Adaptive Response Policies, Action Types, Decision Audit Logs,
Rate Limiting, IP Bans, Quarantine, and SIEM Forwarding.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field
from backend.app.schemas.anomaly import SeverityLevel


class PolicyAction(str, Enum):
    """Actions the adaptive response engine can execute."""
    ALLOW = "allow"          # Explicit allow or bypass further inspection
    THROTTLE = "throttle"    # Rate limit / slow down request frequency
    CHALLENGE = "challenge"  # Issue step-up challenge (MFA, CAPTCHA, re-auth)
    BLOCK = "block"          # Reject request immediately (HTTP 403 / drop)
    QUARANTINE = "quarantine"# Isolate IP or client identity for scrutiny


class PolicyCondition(BaseModel):
    """Conditions required for a policy rule to match an event or anomaly."""
    min_risk_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Minimum risk score (0-100)")
    max_risk_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Maximum risk score (0-100)")
    severities: Optional[List[SeverityLevel]] = Field(None, description="Matching severity levels")
    attack_types: Optional[List[str]] = Field(None, description="Attack categories (e.g. sqli, traversal, bola, brute_force)")
    endpoint_pattern: Optional[str] = Field(None, description="Regex or wildcard pattern for endpoint path")
    http_methods: Optional[List[str]] = Field(None, description="HTTP methods (e.g. ['POST', 'DELETE'])")
    client_ip_cidr: Optional[str] = Field(None, description="Client IP or CIDR block (e.g. '198.51.100.0/24')")
    max_client_reputation: Optional[float] = Field(None, ge=0.0, le=100.0, description="Trigger if reputation <= value")
    auth_types: Optional[List[str]] = Field(None, description="Authentication types (e.g. ['none', 'api_key'])")


class PolicyRule(BaseModel):
    """A declarative security policy rule."""
    policy_id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Human-readable policy name")
    description: str = Field("", description="Detailed explanation of the policy intent")
    is_enabled: bool = Field(True, description="Whether this policy is active")
    priority: int = Field(100, ge=1, le=1000, description="Evaluation order (lower number = evaluated first)")
    conditions: PolicyCondition = Field(default_factory=PolicyCondition)
    action: PolicyAction = Field(..., description="Action to take when conditions match")
    action_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the action (e.g. ban_duration_seconds, rate_limit_rpm, webhook_url)",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PolicyDecision(BaseModel):
    """Immutable audit trail of an adaptive protection decision."""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str = Field(..., description="ID of the triggering API event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_ip: str
    endpoint: str
    http_method: str
    risk_score: float = Field(0.0, ge=0.0, le=100.0)
    severity: SeverityLevel = SeverityLevel.INFO
    action_taken: PolicyAction
    matched_policy_id: Optional[str] = None
    matched_policy_name: Optional[str] = None
    reason: str = Field(..., description="Detailed explanation of why the action was taken")
    action_details: Dict[str, Any] = Field(default_factory=dict, description="Action execution details")
    is_active: bool = True


class BlocklistEntry(BaseModel):
    """Represents an active temporary or permanent IP ban."""
    ip: str = Field(..., description="Banned IPv4 or IPv6 address")
    reason: str = Field(..., description="Reason for ban")
    banned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(None, description="None indicates permanent ban")
    policy_id: Optional[str] = None
    is_active: bool = True

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class QuarantineEntry(BaseModel):
    """Represents an entity isolated in quarantine for security review."""
    client_ip: str
    client_id: Optional[str] = None
    quarantined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str
    policy_id: Optional[str] = None
    is_active: bool = True


class ThrottleState(BaseModel):
    """Real-time throttle status for a client or IP."""
    client_ip: str
    endpoint: Optional[str] = None
    rate_limit_rpm: int
    current_count: int
    is_throttled: bool
    retry_after_seconds: int = 0


class PolicyEvaluationRequest(BaseModel):
    """Request payload to test or dry-run policy evaluation."""
    client_ip: str
    endpoint: str
    http_method: str = "GET"
    risk_score: float = 0.0
    severity: SeverityLevel = SeverityLevel.INFO
    attack_types: List[str] = Field(default_factory=list)
    reputation_score: Optional[float] = None
    auth_type: str = "none"


class PolicyEvaluationResponse(BaseModel):
    """Result of policy evaluation."""
    action: PolicyAction
    matched_policy_id: Optional[str] = None
    matched_policy_name: Optional[str] = None
    reason: str
    action_params: Dict[str, Any] = Field(default_factory=dict)
    applied_in_dry_run: bool = False


class PolicyStats(BaseModel):
    """Operational statistics for adaptive protection policies."""
    total_policies: int
    enabled_policies: int
    total_decisions_evaluated: int
    actions_breakdown: Dict[str, int]
    active_banned_ips_count: int
    active_quarantined_count: int
    total_webhooks_dispatched: int
    total_siem_events_forwarded: int
