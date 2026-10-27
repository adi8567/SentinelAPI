"""SentinelAPI Chaos & Resilience Integration Tests.

Validates platform resilience under adversarial chaos conditions:
- Corrupted, malformed, and truncated log payloads.
- Rate-limiter sliding window exhaustion and recovery.
- Temporary IP ban auto-expiration under TTL.
- Storage query resilience under edge-case filtering.
"""

import asyncio
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from backend.app.services.policy.actions.ban_manager import ip_ban_manager
from backend.app.services.policy.actions.throttler import throttler


@pytest.mark.asyncio
async def test_corrupted_and_malformed_logs_resilience(async_client: AsyncClient):
    """Verifies that invalid or corrupted log entries are handled gracefully without pipeline crash."""
    corrupted_batch = [
        "NOT A VALID LOG LINE AT ALL",
        '192.168.1.1 - - [invalid_date] "BROKEN_HTTP_LINE',
        "",
        "   ",
        '{"invalid_json": true, "missing_all_required_fields": 123}',
        '198.51.100.1 - - [27/Oct/2026:10:00:00 +0000] "GET /api/v1/valid HTTP/1.1" 200 450 "-" "curl/7.81"',
    ]

    resp = await async_client.post(
        "/api/v1/ingest/raw",
        json={"source_type": "auto", "logs": corrupted_batch},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Valid log must be accepted, invalid logs rejected with error details
    assert data["accepted_count"] >= 1
    assert data["rejected_count"] >= 1
    assert len(data["parse_errors"]) >= 1


@pytest.mark.asyncio
async def test_rate_limiter_recovery_after_burst():
    """Validates sliding window throttler enforces limit and automatically recovers after window passes."""
    key = "chaos_client_192.0.2.77"
    limit_rpm = 3
    window_sec = 1

    # Consume up to the limit
    for _ in range(limit_rpm):
        is_throttled, _, count = await throttler.record_and_check(key, limit_rpm=limit_rpm, window_seconds=window_sec)
        assert is_throttled is False

    # Next attempt must be throttled
    is_throttled_over, retry_after, count_over = await throttler.record_and_check(
        key, limit_rpm=limit_rpm, window_seconds=window_sec
    )
    assert is_throttled_over is True
    assert retry_after >= 1

    # Wait for window to expire
    await asyncio.sleep(1.2)

    # Must recover and permit requests again
    is_throttled_rec, _, _ = await throttler.record_and_check(
        key, limit_rpm=limit_rpm, window_seconds=window_sec
    )
    assert is_throttled_rec is False


@pytest.mark.asyncio
async def test_temporary_ip_ban_ttl_auto_expiration():
    """Validates temporary IP ban enforcement and automatic expiration after TTL."""
    test_ip = "198.51.100.222"

    # Apply 1-second temporary ban
    await ip_ban_manager.ban_ip(
        ip=test_ip,
        duration_seconds=1,
        reason="Chaos test temporary ban",
    )

    # Immediately check ban status
    is_banned, entry = await ip_ban_manager.is_banned(test_ip)
    assert is_banned is True
    assert entry is not None
    assert entry.reason == "Chaos test temporary ban"

    # Wait for TTL expiration
    await asyncio.sleep(1.2)

    # Ban must have auto-expired
    is_banned_post, entry_post = await ip_ban_manager.is_banned(test_ip)
    assert is_banned_post is False
    assert entry_post is None
