"""SentinelAPI Forensic Investigation Schemas.

Data models for Root-Cause Analysis, Client Behavioral Profiling,
Endpoint Deviation Investigation, and Sequence Flow Graph Visualizations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventForensicTrace(BaseModel):
    event_id: str
    timestamp: datetime
    raw_log: Optional[str] = None
    normalized_event: Dict[str, Any]
    anomaly_details: Optional[Dict[str, Any]] = None
    detector_scores: Dict[str, float] = Field(default_factory=dict)
    contributing_factors: List[str] = Field(default_factory=list)
    policy_decision: Optional[Dict[str, Any]] = None
    client_reputation: float
    endpoint_baseline: Optional[Dict[str, Any]] = None
    session_context: Optional[Dict[str, Any]] = None


class ClientInvestigation(BaseModel):
    client_ip: str
    reputation_score: float
    total_requests: int
    error_count: int
    distinct_endpoints_count: int
    observed_endpoints: List[str]
    is_banned: bool
    ban_details: Optional[Dict[str, Any]] = None
    is_quarantined: bool
    past_anomalies_count: int
    past_anomalies: List[Dict[str, Any]]
    recent_sessions: List[Dict[str, Any]]


class EndpointInvestigation(BaseModel):
    endpoint_id: str
    http_method: str
    path_template: str
    risk_level: str
    total_calls: int
    status_distribution: Dict[str, int]
    baseline_metrics: Optional[Dict[str, Any]] = None
    observed_parameters: Dict[str, Any]
    recent_anomalies_count: int
    recent_anomalies: List[Dict[str, Any]]


class SequenceFlowNode(BaseModel):
    id: str
    label: str
    call_count: int
    risk_level: str = "low"


class SequenceFlowLink(BaseModel):
    source: str
    target: str
    value: int
    probability: float


class SequenceFlowGraph(BaseModel):
    nodes: List[SequenceFlowNode]
    links: List[SequenceFlowLink]
