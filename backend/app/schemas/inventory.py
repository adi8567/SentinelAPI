"""SentinelAPI Inventory Schemas.

Data models for Endpoints, Clients, Users/Service Accounts, and Sessions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClientType(str, Enum):
    IP = "ip"
    USER = "user"
    SERVICE_ACCOUNT = "service_account"


class ParameterInfo(BaseModel):
    name: str
    location: str = "query"  # "query", "header", "path"
    observed_types: List[str] = Field(default_factory=list)
    sample_values: List[str] = Field(default_factory=list)
    is_required: bool = False


class EndpointRecord(BaseModel):
    """Represents a discovered unique API endpoint pattern."""
    endpoint_id: str = Field(description="Unique endpoint hash/identifier")
    http_method: str = Field(..., description="HTTP Verb (GET, POST, etc.)")
    path_template: str = Field(..., description="Parameterized path (e.g. /api/v1/users/{id})")
    sample_raw_paths: List[str] = Field(default_factory=list, description="Recent verbatim paths observed")
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    call_count: int = Field(default=0, ge=0)
    parameters: Dict[str, ParameterInfo] = Field(default_factory=dict)
    is_authenticated: bool = Field(default=False)
    auth_types_observed: List[str] = Field(default_factory=list)
    status_codes_observed: Dict[str, int] = Field(default_factory=dict)
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClientRecord(BaseModel):
    """Represents an API consumer identity (IP, User Account, or Service Principal)."""
    client_id: str = Field(description="Client identifier (IP address or auth subject hash)")
    client_type: ClientType = Field(default=ClientType.IP)
    ip_address: str
    user_agents_observed: List[str] = Field(default_factory=list)
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_requests: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    distinct_endpoints_count: int = Field(default=0, ge=0)
    observed_endpoints: List[str] = Field(default_factory=list)
    geo_country: Optional[str] = None
    reputation_score: float = Field(default=100.0, ge=0.0, le=100.0)


class SessionRecord(BaseModel):
    """Represents a client behavioral interaction session."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    identity: Optional[str] = None
    client_ip: str
    user_agent: str = "unknown"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_count: int = Field(default=0, ge=0)
    endpoint_sequence: List[str] = Field(default_factory=list)
    status_sequence: List[int] = Field(default_factory=list)


class InventorySummary(BaseModel):
    total_endpoints: int
    endpoints_by_method: Dict[str, int]
    endpoints_by_risk: Dict[str, int]
    total_clients: int
    authenticated_endpoints_count: int
