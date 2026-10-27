"""Integration test for full closed-loop detection -> decision -> action system with real data."""

from pathlib import Path
import pytest
from httpx import AsyncClient
from backend.app.schemas.events import LogSource
from backend.app.schemas.policy import PolicyAction
from backend.app.services.ingestion.pipeline import ingestion_pipeline
from backend.app.services.policy.actions.ban_manager import ip_ban_manager
from backend.app.services.policy.actions.siem_forwarder import siem_forwarder
from backend.app.services.policy.engine import policy_engine

DATASETS_DIR = Path(__file__).resolve().parents[3] / "data" / "real_datasets"


@pytest.mark.asyncio
async def test_closed_loop_adaptive_protection_on_real_attacks():
    # 1. Reset state
    await policy_engine.reset()
    siem_forwarder.clear()

    # 2. Ingest real attack dataset
    attack_file = DATASETS_DIR / "real_api_sec_attacks.log"
    assert attack_file.exists(), f"Real attack dataset not found at {attack_file}"

    with open(attack_file, "r", encoding="utf-8") as f:
        attack_lines = [line.strip() for line in f if line.strip()]

    result = await ingestion_pipeline.ingest_raw_batch(
        raw_lines=attack_lines,
        source_type=LogSource.AUTO,
        gateway_id="test-closed-loop",
    )
    assert result.success is True
    assert result.accepted_count > 0

    # 3. Verify Policy Enforcement Decisions
    decisions = await policy_engine.get_decisions(limit=100)
    assert len(decisions) >= len(attack_lines)

    # 4. Assert SQLi probe resulted in BLOCK and IP Ban
    block_decisions = [d for d in decisions if d.action_taken == PolicyAction.BLOCK]
    assert len(block_decisions) >= 1

    # Check the SQLi attacker IP was banned
    sqli_ip = "203.0.113.200"
    is_banned, ban_entry = await ip_ban_manager.is_banned(sqli_ip)
    assert is_banned is True
    assert ban_entry is not None
    assert ban_entry.ip == sqli_ip

    # Assert benign traffic was ALLOWED
    allow_decisions = [d for d in decisions if d.action_taken == PolicyAction.ALLOW]
    assert len(allow_decisions) >= 1
    assert any(d.client_ip == "198.51.100.42" for d in allow_decisions)

    # 5. Assert Credential Stuffing brute force was THROTTLED
    throttle_decisions = [d for d in decisions if d.action_taken == PolicyAction.THROTTLE]
    assert len(throttle_decisions) >= 1
    assert any("/api/v1/auth/login" in d.endpoint for d in throttle_decisions)

    # 6. Assert SIEM Forwarder received CEF records
    siem_stats = siem_forwarder.get_stats()
    assert siem_stats["total_siem_events_forwarded"] >= len(block_decisions)
    assert "CEF:0|SentinelAPI|AdaptiveProtection" in siem_stats["last_cef_record"]

    # 7. Test subsequent request from banned IP is immediately BLOCKED at pre-check
    from backend.app.schemas.events import ApiEvent
    from datetime import datetime, timezone

    subsequent_event = ApiEvent(
        timestamp=datetime.now(timezone.utc),
        source_type=LogSource.NGINX,
        http_method="GET",
        path="/api/v1/catalog",
        raw_path="/api/v1/catalog",
        status_code=200,
        latency_ms=10.0,
        client_ip=sqli_ip,
    )
    pre_check_decision = await policy_engine.evaluate(subsequent_event, anomaly=None)
    assert pre_check_decision.action_taken == PolicyAction.BLOCK
    assert pre_check_decision.matched_policy_id == "active_ip_ban"
