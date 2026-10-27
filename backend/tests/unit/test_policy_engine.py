"""Unit tests for Policy Evaluation Engine."""

from datetime import datetime, timezone
import pytest
from backend.app.schemas.anomaly import AnomalyRecord, SeverityLevel
from backend.app.schemas.events import ApiEvent, LogSource
from backend.app.schemas.policy import (
    PolicyAction,
    PolicyCondition,
    PolicyRule,
)
from backend.app.services.policy.actions.ban_manager import ip_ban_manager
from backend.app.services.policy.engine import PolicyEngine


@pytest.fixture
async def policy_engine_instance():
    engine = PolicyEngine()
    await engine.initialize()
    await engine.reset()
    yield engine
    await engine.reset()


@pytest.mark.asyncio
async def test_policy_allow_health_endpoint(policy_engine_instance):
    event = ApiEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSource.NGINX,
        http_method="GET",
        path="/health",
        raw_path="/health",
        status_code=200,
        latency_ms=2.5,
        client_ip="10.0.0.5",
    )
    decision = await policy_engine_instance.evaluate(event, anomaly=None)
    assert decision.action_taken == PolicyAction.ALLOW
    assert decision.matched_policy_id == "pol_allow_internal_health"


@pytest.mark.asyncio
async def test_policy_block_critical_sqli(policy_engine_instance):
    event = ApiEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSource.NGINX,
        http_method="GET",
        path="/api/v1/products",
        raw_path="/api/v1/products?search=shoes%27%20OR%201=1--",
        query_params={"search": "shoes' OR 1=1--"},
        status_code=400,
        latency_ms=120.0,
        client_ip="198.51.100.42",
    )
    anomaly = AnomalyRecord(
        event_id=event.event_id,
        endpoint_id="products_get",
        http_method=event.http_method,
        path=event.path,
        client_ip=event.client_ip,
        client_id="anon",
        risk_score=85.0,
        severity=SeverityLevel.CRITICAL,
        contributing_factors=["SQL Injection signature detected: quote/union/tautology pattern in query parameter"],
    )

    decision = await policy_engine_instance.evaluate(event, anomaly)
    assert decision.action_taken == PolicyAction.BLOCK
    assert decision.matched_policy_id == "pol_block_critical_attacks"


@pytest.mark.asyncio
async def test_policy_throttle_brute_force(policy_engine_instance):
    event = ApiEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSource.ENVOY,
        http_method="POST",
        path="/api/v1/auth/login",
        raw_path="/api/v1/auth/login",
        status_code=401,
        latency_ms=45.0,
        client_ip="198.51.100.99",
    )
    anomaly = AnomalyRecord(
        event_id=event.event_id,
        endpoint_id="auth_login_post",
        http_method=event.http_method,
        path=event.path,
        client_ip=event.client_ip,
        client_id="anon",
        risk_score=80.0,
        severity=SeverityLevel.CRITICAL,
        contributing_factors=["Brute force / Credential stuffing burst on authentication endpoint (/api/v1/auth/login)"],
    )

    decision = await policy_engine_instance.evaluate(event, anomaly)
    assert decision.action_taken == PolicyAction.THROTTLE
    assert decision.matched_policy_id == "pol_throttle_brute_force"


@pytest.mark.asyncio
async def test_policy_pre_existing_ban_enforced(policy_engine_instance):
    ip = "198.51.100.77"
    await ip_ban_manager.ban_ip(ip, duration_seconds=3600, reason="Prior attack ban")

    event = ApiEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSource.NGINX,
        http_method="GET",
        path="/api/v1/items",
        raw_path="/api/v1/items",
        status_code=200,
        latency_ms=15.0,
        client_ip=ip,
    )

    decision = await policy_engine_instance.evaluate(event, anomaly=None)
    assert decision.action_taken == PolicyAction.BLOCK
    assert decision.matched_policy_id == "active_ip_ban"
    assert "Prior attack ban" in decision.reason


@pytest.mark.asyncio
async def test_policy_custom_rule_priority(policy_engine_instance):
    # Add high priority rule matching specific CIDR
    custom_rule = PolicyRule(
        policy_id="pol_custom_trusted_cidr",
        name="Allow Trusted Subnet",
        is_enabled=True,
        priority=1,  # Lower number = higher priority than all defaults
        conditions=PolicyCondition(
            client_ip_cidr="192.168.100.0/24",
        ),
        action=PolicyAction.ALLOW,
    )
    await policy_engine_instance.add_or_update_rule(custom_rule)

    event = ApiEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSource.NGINX,
        http_method="GET",
        path="/api/v1/data",
        raw_path="/api/v1/data",
        status_code=200,
        latency_ms=10.0,
        client_ip="192.168.100.45",
    )

    decision = await policy_engine_instance.evaluate(event, anomaly=None)
    assert decision.action_taken == PolicyAction.ALLOW
    assert decision.matched_policy_id == "pol_custom_trusted_cidr"
