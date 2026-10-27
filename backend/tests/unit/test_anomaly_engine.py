"""Unit Tests for Ensemble Anomaly Detection Engine."""

from datetime import datetime, timezone
import pytest
from backend.app.schemas.anomaly import SeverityLevel
from backend.app.schemas.events import ApiEvent, LogSource
from backend.app.services.detection.engine import AnomalyDetectionEngine


def test_ensemble_scoring_and_severity():
    engine = AnomalyDetectionEngine(anomaly_threshold=35.0)

    # Attack event with SQL injection
    attack_ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/api/v1/search",
        raw_path="/api/v1/search?q=' OR '1'='1",
        query_params={"q": "' OR '1'='1"},
        status_code=400,
        latency_ms=45.0,
        client_ip="198.51.100.7",
    )

    anomaly = engine.score_event(attack_ev)
    assert anomaly is not None
    assert anomaly.risk_score >= 80.0
    assert anomaly.severity == SeverityLevel.CRITICAL
    assert len(anomaly.contributing_factors) >= 1
    assert "signature" in anomaly.detector_scores
    assert anomaly.detector_scores["signature"] >= 80.0


def test_benign_event_scoring():
    engine = AnomalyDetectionEngine(anomaly_threshold=40.0)

    normal_ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/api/v1/health",
        raw_path="/api/v1/health",
        status_code=200,
        latency_ms=2.0,
        client_ip="127.0.0.1",
    )

    anomaly = engine.score_event(normal_ev)
    assert anomaly is None
