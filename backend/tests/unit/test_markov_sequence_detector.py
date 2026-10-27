"""Unit Tests for Markov Sequence Anomaly Detector."""

from datetime import datetime, timezone
import pytest
from backend.app.schemas.events import ApiEvent, LogSource
from backend.app.services.detection.models.sequence_markov import MarkovSequenceDetector


def test_markov_sequence_transitions():
    detector = MarkovSequenceDetector(rare_transition_threshold=0.05)

    # Train with valid e-commerce sessions: /cart -> /checkout -> /payments
    sessions = [
        ["/cart", "/checkout", "/payments"],
        ["/cart", "/checkout", "/payments"],
        ["/cart", "/checkout", "/payments"],
        ["/cart", "/checkout", "/payments"],
        ["/cart", "/items", "/cart", "/checkout"],
    ]
    detector.train_from_sessions(sessions)
    assert detector.is_trained is True

    # 1. Normal transition: /cart -> /checkout
    normal_ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="POST",
        path="/checkout",
        raw_path="/checkout",
        status_code=200,
        latency_ms=30.0,
        client_ip="198.51.100.1",
    )
    res_normal = detector.evaluate_transition(normal_ev, previous_endpoint="/cart")
    assert res_normal.is_anomaly is False
    assert res_normal.score == 0.0

    # 2. Unprecedented transition: /cart -> /admin
    anom_ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/admin",
        raw_path="/admin",
        status_code=200,
        latency_ms=20.0,
        client_ip="198.51.100.1",
    )
    res_anom = detector.evaluate_transition(anom_ev, previous_endpoint="/cart")
    assert res_anom.is_anomaly is True
    assert res_anom.score >= 50.0
    assert any("Unprecedented sequence transition" in r for r in res_anom.reasons)
