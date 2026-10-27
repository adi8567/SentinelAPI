"""Unit Tests for Isolation Forest ML Detector."""

from datetime import datetime, timezone
import pytest
from backend.app.schemas.events import ApiEvent, LogSource
from backend.app.services.detection.models.isolation_forest import IsolationForestDetector


def test_isolation_forest_training_and_scoring():
    detector = IsolationForestDetector(contamination=0.1)
    now = datetime.now(timezone.utc)

    # 1. Generate 30 normal events
    training_events = [
        ApiEvent(
            source_type=LogSource.GENERIC_HTTP,
            http_method="GET",
            path="/api/v1/orders",
            raw_path="/api/v1/orders",
            status_code=200,
            latency_ms=20.0 + (i * 1.5),
            client_ip="198.51.100.1",
            request_size_bytes=100 + (i * 10),
            response_size_bytes=400 + (i * 20),
            timestamp=now,
        )
        for i in range(30)
    ]

    success = detector.fit(training_events)
    assert success is True
    assert detector.is_trained is True

    # 2. Evaluate normal event
    normal_ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/api/v1/orders",
        raw_path="/api/v1/orders",
        status_code=200,
        latency_ms=26.0,
        client_ip="198.51.100.1",
        request_size_bytes=150,
        response_size_bytes=500,
        timestamp=now,
    )
    res_normal = detector.evaluate(normal_ev)
    assert res_normal.score < 50.0

    # 3. Evaluate multivariate outlier (huge latency + massive payload + error status)
    outlier_ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/api/v1/orders",
        raw_path="/api/v1/orders",
        status_code=500,
        latency_ms=1500.0,
        client_ip="198.51.100.1",
        request_size_bytes=85000,
        response_size_bytes=120000,
        timestamp=now,
    )
    res_outlier = detector.evaluate(outlier_ev)
    assert res_outlier.score >= 50.0
    assert res_outlier.is_anomaly is True
    assert any("Multivariate isolation outlier" in r for r in res_outlier.reasons)
