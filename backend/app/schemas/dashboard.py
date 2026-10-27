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


class TrafficTimeseriesPoint(BaseModel):
    timestamp: datetime
    total_requests: int
    error_requests: int
    anomaly_requests: int
    avg_latency_ms: float


class AnomalyTimeseriesPoint(BaseModel):
    timestamp: datetime
    critical: int
    high: int
    medium: int
    low: int
    total: int


class RiskDistributionData(BaseModel):
    histogram: Dict[str, int]
    p25: float
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float
    min_score: float
    max_score: float


class TopEndpointAnomalies(BaseModel):
    endpoint_id: str
    http_method: str
    path_template: str
    total_calls: int
    anomaly_count: int
    highest_risk_score: float
    risk_level: str


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


class ActionsBreakdownData(BaseModel):
    actions: Dict[str, int]
    active_bans_count: int
    active_quarantines_count: int
    total_decisions: int
