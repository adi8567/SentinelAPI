"""Unit tests for SIEM CEF and Syslog formatting."""

from datetime import datetime, timezone
import pytest
from backend.app.schemas.anomaly import SeverityLevel
from backend.app.schemas.policy import PolicyAction, PolicyDecision
from backend.app.services.policy.actions.siem_forwarder import SIEMForwarder


def test_format_cef_critical_block():
    forwarder = SIEMForwarder()
    decision = PolicyDecision(
        event_id="evt_test_123",
        timestamp=datetime.now(timezone.utc),
        client_ip="198.51.100.42",
        endpoint="/api/v1/users",
        http_method="GET",
        risk_score=85.0,
        severity=SeverityLevel.CRITICAL,
        action_taken=PolicyAction.BLOCK,
        matched_policy_id="pol_block_critical",
        matched_policy_name="Block Critical Attacks",
        reason="SQL injection probe detected in query parameter",
        action_details={"ban_duration_seconds": 3600},
    )

    cef = forwarder.format_cef(decision)
    assert cef.startswith("CEF:0|SentinelAPI|AdaptiveProtection|1.0|POL_BLOCK|Adaptive Protection: BLOCK|10|")
    assert "src=198.51.100.42" in cef
    assert "request=/api/v1/users" in cef
    assert "act=block" in cef
    assert "cs1=pol_block_critical" in cef
    assert "cfp1=85.0" in cef
    assert "externalId=evt_test_123" in cef


def test_format_syslog():
    forwarder = SIEMForwarder()
    decision = PolicyDecision(
        event_id="evt_test_456",
        timestamp=datetime.now(timezone.utc),
        client_ip="192.168.1.1",
        endpoint="/health",
        http_method="GET",
        risk_score=0.0,
        severity=SeverityLevel.INFO,
        action_taken=PolicyAction.ALLOW,
        reason="Normal baseline traffic",
    )

    syslog = forwarder.format_syslog(decision)
    assert "<134>1 " in syslog
    assert "sentinelapi.local sentinelapi - POLICY_AUDIT" in syslog
    assert 'action="allow"' in syslog
    assert "CEF:0|SentinelAPI|AdaptiveProtection" in syslog


def test_siem_forward_records_buffer():
    forwarder = SIEMForwarder()
    decision = PolicyDecision(
        event_id="evt_test_789",
        timestamp=datetime.now(timezone.utc),
        client_ip="10.0.0.1",
        endpoint="/metrics",
        http_method="GET",
        action_taken=PolicyAction.ALLOW,
        reason="Health probe",
    )

    cef_msg = forwarder.forward(decision)
    assert forwarder.get_stats()["total_siem_events_forwarded"] == 1
    assert forwarder.get_stats()["last_cef_record"] == cef_msg
