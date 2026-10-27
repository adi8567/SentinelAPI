"""Unit tests for SentinelAPI Prometheus Metrics Exporter."""

import pytest
from backend.app.core.metrics import (
    ANOMALIES_DETECTED_TOTAL,
    ANOMALY_RISK_SCORE,
    EVENTS_INGESTED_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    export_metrics,
)


def test_metrics_collection_and_increment():
    # Increment counters
    HTTP_REQUESTS_TOTAL.labels(method="GET", endpoint="/api/v1/test", status_code="200").inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method="GET", endpoint="/api/v1/test").observe(0.025)
    EVENTS_INGESTED_TOTAL.labels(source_type="nginx").inc(10)
    ANOMALIES_DETECTED_TOTAL.labels(severity="critical", primary_detector="signature").inc()
    ANOMALY_RISK_SCORE.observe(88.5)

    # Export Prometheus text format
    raw_output = export_metrics().decode("utf-8")

    assert "sentinel_http_requests_total" in raw_output
    assert "sentinel_events_ingested_total" in raw_output
    assert "sentinel_anomalies_detected_total" in raw_output
    assert "sentinel_anomaly_risk_score" in raw_output
    assert 'primary_detector="signature"' in raw_output
    assert 'source_type="nginx"' in raw_output
