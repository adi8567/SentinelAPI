"""SentinelAPI Dashboard Visualization Schemas.

Data models for rich aggregated metrics, time-series graphs, risk score distributions,
endpoint health matrices, geographic maps, and action summaries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DashboardOverview(BaseModel):
    total_requests: int
    total_anomalies: int
    anomaly_rate_percent: float
    blocked_attacks: int
    throttled_requests: int
    active_banned_ips: int
    monitored_endpoints_count: int
    unique_clients_count: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    system_health: str = "HEALTHY"

    # Frontend compatibility fields
    active_alerts: int = 0
    total_endpoints: int = 0
    total_clients: int = 0
    banned_clients_count: int = 0
    quarantined_clients_count: int = 0
    policy_enforcements_count: int = 0
    p99_latency_ms: float = 0.0
    status_code_distribution: Dict[str, int] = Field(default_factory=dict)


class TrafficTimeseriesPoint(BaseModel):
    timestamp: datetime
    total_requests: int
    error_requests: int
    anomaly_requests: int
    avg_latency_ms: float

    # Frontend compatibility fields
    bucket_time: Optional[str] = None
    status_2xx: int = 0
    status_3xx: int = 0
    status_4xx: int = 0
    status_5xx: int = 0
    p95_latency_ms: float = 0.0


class AnomalyTimeseriesPoint(BaseModel):
    timestamp: datetime
    critical: int
    high: int
    medium: int
    low: int
    total: int

    # Frontend compatibility fields
    bucket_time: Optional[str] = None
    total_anomalies: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    avg_risk_score: float = 0.0


class RiskDistributionData(BaseModel):
    histogram: Any  # Supports both Dict[str, int] and List[Dict[str, Any]]
    p25: float
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float
    min_score: float = 0.0
    max_score: float = 0.0
    mean: float = 0.0


class TopEndpointAnomalies(BaseModel):
    endpoint_id: str
    http_method: str
    path_template: str
    total_calls: int
    anomaly_count: int
    highest_risk_score: float
    risk_level: str

    # Frontend compatibility fields
    endpoint: str = ""
    max_risk_score: float = 0.0
    primary_detector: str = "Ensemble"
    last_anomaly_at: str = "Recently"


class EndpointHealthMetric(BaseModel):
    endpoint_id: str
    path_template: str
    http_method: str
    total_requests: int
    error_count: int
    error_rate_percent: float
    avg_latency_ms: float
    health_status: str  # healthy, degraded, critical


class GeoDistributionPoint(BaseModel):
    country_code: str
    country_name: str
    request_count: int
    anomaly_count: int
    threat_score: float = 0.0


class ActionsBreakdownData(BaseModel):
    actions: Dict[str, int]
    active_bans_count: int
    active_quarantines_count: int
    total_decisions: int

    # Frontend compatibility fields
    total_actions: int = 0
    allow_count: int = 0
    throttle_count: int = 0
    challenge_count: int = 0
    block_count: int = 0
    quarantine_count: int = 0
