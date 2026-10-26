"""SentinelAPI Baseline Learning Schemas.

Models for statistical behavioral baselines per endpoint and per client.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class BaselineWindow(str, Enum):
    GLOBAL = "global"
    HOURLY = "hourly"
    DAILY = "daily"


class EndpointBaseline(BaseModel):
    """Statistical behavioral baseline for an API endpoint."""
    baseline_id: str
    endpoint_id: str
    window_type: BaselineWindow = BaselineWindow.GLOBAL
    sample_size: int = Field(default=0, ge=0)

    # Request rate metrics (requests/sec)
    req_rate_mean: float = Field(default=0.0, ge=0.0)
    req_rate_std: float = Field(default=0.0, ge=0.0)

    # Latency distribution (ms)
    latency_p50: float = Field(default=0.0, ge=0.0)
    latency_p90: float = Field(default=0.0, ge=0.0)
    latency_p95: float = Field(default=0.0, ge=0.0)
    latency_p99: float = Field(default=0.0, ge=0.0)
    latency_mean: float = Field(default=0.0, ge=0.0)
    latency_std: float = Field(default=0.0, ge=0.0)

    # Request & Response payload distributions (bytes)
    request_size_mean: float = Field(default=0.0, ge=0.0)
    request_size_std: float = Field(default=0.0, ge=0.0)
    response_size_mean: float = Field(default=0.0, ge=0.0)
    response_size_std: float = Field(default=0.0, ge=0.0)

    # Categorical probability distribution
    status_code_distribution: Dict[str, float] = Field(default_factory=dict)

    # Seasonality profiles: relative weight (0.0 to 1.0)
    seasonality_hour_of_day: Dict[int, float] = Field(default_factory=dict)
    seasonality_day_of_week: Dict[int, float] = Field(default_factory=dict)

    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)


class ClientBaseline(BaseModel):
    """Statistical behavioral baseline for a client/consumer identity."""
    client_id: str
    sample_size: int = Field(default=0, ge=0)
    req_rate_mean: float = Field(default=0.0, ge=0.0)
    req_rate_std: float = Field(default=0.0, ge=0.0)
    error_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_latency_ms: float = Field(default=0.0, ge=0.0)
    top_endpoints: List[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)


class RecomputeBaselinesResult(BaseModel):
    success: bool
    endpoints_computed: int
    clients_computed: int
    total_events_analyzed: int
    execution_time_ms: float
