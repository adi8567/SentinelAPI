"""Unit Tests for OWASP API Attack Signature Detector."""

from datetime import datetime, timezone
import pytest
from backend.app.schemas.events import ApiEvent, LogSource
from backend.app.services.detection.models.signature_detector import SignatureThreatDetector


def test_sqli_detection():
    detector = SignatureThreatDetector()
    ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/api/v1/products",
        raw_path="/api/v1/products?search=shoes%27%20OR%20%271%27=%271",
        query_params={"search": "shoes' OR '1'='1"},
        status_code=400,
        latency_ms=15.0,
        client_ip="203.0.113.5",
    )
    res = detector.evaluate(ev)
    assert res.is_anomaly is True
    assert res.score >= 80.0
    assert any("SQL Injection" in r for r in res.reasons)


def test_path_traversal_detection():
    detector = SignatureThreatDetector()
    ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/api/v1/files/download",
        raw_path="/api/v1/files/download?file=../../../../etc/passwd",
        query_params={"file": "../../../../etc/passwd"},
        status_code=400,
        latency_ms=10.0,
        client_ip="203.0.113.5",
    )
    res = detector.evaluate(ev)
    assert res.is_anomaly is True
    assert res.score >= 80.0
    assert any("traversal" in r.lower() for r in res.reasons)


def test_scanner_user_agent_detection():
    detector = SignatureThreatDetector()
    ev = ApiEvent(
        source_type=LogSource.GENERIC_HTTP,
        http_method="GET",
        path="/api/v1/items",
        raw_path="/api/v1/items",
        status_code=200,
        latency_ms=12.0,
        client_ip="203.0.113.5",
        user_agent="sqlmap/1.7#stable",
    )
    res = detector.evaluate(ev)
    assert res.is_anomaly is True
    assert any("scanner User-Agent" in r for r in res.reasons)


def test_bola_idor_detection():
    detector = SignatureThreatDetector()
    now = datetime.now(timezone.utc)
    ip = "198.51.100.99"

    # Simulate 3 successive 403s on different IDs
    for uid in [1001, 1002, 1003]:
        ev = ApiEvent(
            source_type=LogSource.GENERIC_HTTP,
            http_method="GET",
            path=f"/api/v1/users/{uid}",
            raw_path=f"/api/v1/users/{uid}",
            status_code=403,
            latency_ms=10.0,
            client_ip=ip,
            timestamp=now,
        )
        res = detector.evaluate(ev)

    assert res.is_anomaly is True
    assert res.score >= 75.0
    assert any("BOLA / IDOR" in r for r in res.reasons)
