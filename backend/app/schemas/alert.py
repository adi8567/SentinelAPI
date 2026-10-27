"""SentinelAPI Security Alerts & Incident Schemas.

Data models for Security Alert management, investigation status, and mitigation tracking.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field
from backend.app.schemas.anomaly import SeverityLevel
from backend.app.schemas.policy import PolicyAction


class AlertStatus(str, Enum):
    NEW = "new"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"


class AlertRecord(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    anomaly_id: str
    event_id: str
    title: str
    description: str
    severity: SeverityLevel
    risk_score: float
    status: AlertStatus = AlertStatus.NEW
    endpoint: str
    http_method: str
    client_ip: str
    client_id: str
    assignee: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    contributing_factors: List[str] = Field(default_factory=list)
    event_snapshot: Dict[str, Any] = Field(default_factory=dict)
    mitigation_action: Optional[PolicyAction] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    assignee: Optional[str] = None
    note: Optional[str] = None


class AlertMitigateRequest(BaseModel):
    action: PolicyAction = PolicyAction.BLOCK
    ban_duration_seconds: Optional[int] = 3600
    reason: str = "Manual alert mitigation"
