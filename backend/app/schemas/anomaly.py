"""SentinelAPI Anomaly Detection Schemas.

Data models for Anomaly Events, Threat Severity, Detector Diagnosics, and Explainability.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectorType(str, Enum):
    STATISTICAL = "statistical"
    ISOLATION_FOREST = "isolation_forest"
    MARKOV_SEQUENCE = "markov_sequence"
    CONTEXTUAL = "contextual"
    SIGNATURE = "signature"
    ENSEMBLE = "ensemble"


class DetectorResult(BaseModel):
    """Output from an individual anomaly detector."""
    detector_name: str
    is_anomaly: bool
    score: float = Field(..., ge=0.0, le=100.0, description="Risk contribution (0-100)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnomalyRecord(BaseModel):
    """Represents a scored anomalous API interaction with full context and explainability."""
    anomaly_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str = Field(description="Foreign key to the underlying ApiEvent")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    endpoint_id: str
    http_method: str
    path: str
    client_ip: str
    client_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Composite Risk Score (0-100)")
    severity: SeverityLevel
    primary_detector: str = "ensemble"
    detector_scores: Dict[str, float] = Field(default_factory=dict)
    contributing_factors: List[str] = Field(default_factory=list, description="Human-explainable diagnostics")
    event_snapshot: Dict[str, Any] = Field(default_factory=dict, description="Snapshot of the original event")
    is_mitigated: bool = False
    is_false_positive: bool = False
    model_version: str = "v1.0.0"


class AnomalyStats(BaseModel):
    total_anomalies: int
    severity_breakdown: Dict[str, int]
    top_anomalous_endpoints: List[Dict[str, Any]]
    top_suspicious_clients: List[Dict[str, Any]]
    risk_score_distribution: Dict[str, int]  # e.g., "0-20", "20-40", "40-60", "60-80", "80-100"
    recent_anomalies_count_1h: int


class ModelRetrainResult(BaseModel):
    success: bool
    models_retrained: List[str]
    training_sample_size: int
    training_duration_ms: float
    new_version: str
