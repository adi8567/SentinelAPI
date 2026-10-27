"""Unit tests for sliding-window rate limiter and throttler."""

import pytest
from backend.app.services.policy.actions.throttler import SlidingWindowThrottler


@pytest.mark.asyncio
async def test_throttler_within_limit():
    throttler = SlidingWindowThrottler(default_window_seconds=60)
    key = "192.168.1.100"

    # Limit 5 RPM: First 5 should succeed
    for i in range(5):
        is_throttled, retry_after, count = await throttler.record_and_check(key, limit_rpm=5)
        assert is_throttled is False
        assert retry_after == 0
        assert count == i + 1


@pytest.mark.asyncio
async def test_throttler_exceeds_limit():
    throttler = SlidingWindowThrottler(default_window_seconds=60)
    key = "192.168.1.101"

    # Fill allowance
    for _ in range(3):
        await throttler.record_and_check(key, limit_rpm=3)

    # 4th request must be throttled
    is_throttled, retry_after, count = await throttler.record_and_check(key, limit_rpm=3)
    assert is_throttled is True
    assert retry_after > 0
    assert count == 4


@pytest.mark.asyncio
async def test_throttler_reset():
    throttler = SlidingWindowThrottler(default_window_seconds=60)
    key = "192.168.1.102"

    for _ in range(5):
        await throttler.record_and_check(key, limit_rpm=3)

    state = await throttler.get_state(key, limit_rpm=3)
    assert state.is_throttled is True

    await throttler.reset(key)
    state = await throttler.get_state(key, limit_rpm=3)
    assert state.is_throttled is False
    assert state.current_count == 0
