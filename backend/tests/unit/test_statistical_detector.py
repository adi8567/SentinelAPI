"""Unit Tests for Statistical Anomaly Detector."""

from datetime import datetime, timezone
import pytest
from backend.app.schemas.baseline import BaselineWindow, EndpointBaseline
from backend.app.schemas.events import ApiEvent, LogSource
from backend.app.services.detection.models.statistical import StatisticalDetector


def test_statistical_latency_spike():
    detector = StatisticalDetector(z_score_threshold=3.0)
    baseline = EndpointBaseline(
        baseline_id="base_1",
        endpoint_id="ep_1",
        sample_size=100,
        latency_mean=30.0,
        latency_std=5.0,
        latency_p99=45.0,
        status_code_distribution={"200": 1.0},
    )

    # Normal request
    normal_ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/items",
        raw_path="/items",
        status_code=200,
        latency_ms=32.0,
        client_ip="198.51.100.1",
    )
    res_normal = detector.evaluate(normal_ev, baseline)
    assert res_normal.is_anomaly is False
    assert res_normal.score == 0.0

    # Latency spike: 90ms with mean 30, std 5 -> Z = 12.0
    spike_ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/items",
        raw_path="/items",
        status_code=200,
        latency_ms=90.0,
        client_ip="198.51.100.1",
    )
    res_spike = detector.evaluate(spike_ev, baseline)
    assert res_spike.is_anomaly is True
    assert res_spike.score > 30.0
    assert any("Latency spike" in r for r in res_spike.reasons)


def test_statistical_rare_status_code():
    detector = StatisticalDetector(rare_status_prob_threshold=0.02)
    baseline = EndpointBaseline(
        baseline_id="base_1",
        endpoint_id="ep_1",
        sample_size=50,
        latency_mean=20.0,
        latency_std=2.0,
        status_code_distribution={"200": 0.99, "400": 0.01},
    )

    # Unexpected 500 error on route
    err_ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/items",
        raw_path="/items",
        status_code=500,
        latency_ms=20.0,
        client_ip="198.51.100.1",
    )
    res_err = detector.evaluate(err_ev, baseline)
    assert res_err.is_anomaly is True
    assert any("Unusual status code 500" in r for r in res_err.reasons)
