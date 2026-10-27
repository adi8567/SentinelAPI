"""SentinelAPI Anomaly Detection and Real-Time Scoring Endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.api.deps import CurrentPrincipal
from backend.app.schemas.anomaly import (
    AnomalyRecord,
    AnomalyStats,
    ModelRetrainResult,
    SeverityLevel,
)
from backend.app.schemas.events import BatchRawLogRequest, LogSource
from backend.app.services.detection.engine import anomaly_engine
from backend.app.services.ingestion.auto_detector import parser_registry

router = APIRouter(prefix="/anomalies", tags=["Anomaly Detection & Threats"])


@router.get("", response_model=List[AnomalyRecord])
async def list_anomalies(
    principal: CurrentPrincipal,
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity level"),
    min_risk_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum risk score threshold"),
    endpoint_id: Optional[str] = Query(None, description="Filter by endpoint ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> List[AnomalyRecord]:
    """Lists real-time detected anomalies with explainable diagnostics and severity ratings."""
    sev_str = severity.value if severity else None
    return anomaly_engine.list_anomalies(
        severity=sev_str,
        min_risk_score=min_risk_score,
        endpoint_id=endpoint_id,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=AnomalyStats)
async def get_anomaly_statistics(
    principal: CurrentPrincipal,
) -> AnomalyStats:
    """Returns anomaly detection rate, severity breakdown, and risk distributions."""
    return AnomalyStats(**anomaly_engine.get_stats())


@router.get("/models/metrics")
async def get_models_metrics(
    principal: CurrentPrincipal,
) -> Dict[str, Any]:
    """Returns training metrics, validation scores, and feature importances for all active ML models."""
    return anomaly_engine.get_models_metrics()


@router.get("/{anomaly_id}", response_model=AnomalyRecord)
async def get_anomaly_detail(
    anomaly_id: str,
    principal: CurrentPrincipal,
) -> AnomalyRecord:
    """Retrieves deep diagnostic details for a specific anomaly event."""
    anomaly = anomaly_engine.get_anomaly(anomaly_id)
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly with ID '{anomaly_id}' not found.",
        )
    return anomaly


@router.post("/retrain", response_model=ModelRetrainResult)
async def retrain_anomaly_models(
    principal: CurrentPrincipal,
) -> ModelRetrainResult:
    """Triggers retraining of Isolation Forest and Markov sequence models on historical traffic."""
    return await anomaly_engine.retrain_models()


@router.post("/score-batch", response_model=List[AnomalyRecord])
async def score_raw_batch(
    payload: BatchRawLogRequest,
    principal: CurrentPrincipal,
) -> List[AnomalyRecord]:
    """Scores a batch of raw logs immediately and returns any detected anomalies."""
    events, errors, _ = parser_registry.parse_with_detection(
        payload.logs,
        gateway_id=payload.gateway_id or "test-gateway",
        forced_source=payload.source_type,
    )

    detected = []
    for ev in events:
        res = anomaly_engine.score_event(ev)
        if res:
            detected.append(res)
    return detected
