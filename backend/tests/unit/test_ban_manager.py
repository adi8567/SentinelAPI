"""Unit tests for IP ban manager."""

from datetime import datetime, timedelta, timezone
import pytest
from backend.app.services.policy.actions.ban_manager import BanManager


@pytest.mark.asyncio
async def test_ban_ip_temporary():
    bm = BanManager()
    ip = "198.51.100.55"

    entry = await bm.ban_ip(ip, duration_seconds=3600, reason="Attack test")
    assert entry.ip == ip
    assert entry.is_active is True
    assert entry.expires_at is not None

    banned, ban_rec = await bm.is_banned(ip)
    assert banned is True
    assert ban_rec.ip == ip


@pytest.mark.asyncio
async def test_ban_ip_permanent():
    bm = BanManager()
    ip = "198.51.100.56"

    entry = await bm.ban_ip(ip, duration_seconds=None, reason="Permanent malicious actor")
    assert entry.expires_at is None

    banned, ban_rec = await bm.is_banned(ip)
    assert banned is True
    assert ban_rec.expires_at is None


@pytest.mark.asyncio
async def test_ban_unban():
    bm = BanManager()
    ip = "198.51.100.57"

    await bm.ban_ip(ip, duration_seconds=100)
    assert (await bm.is_banned(ip))[0] is True

    unbanned = await bm.unban_ip(ip)
    assert unbanned is True
    assert (await bm.is_banned(ip))[0] is False


@pytest.mark.asyncio
async def test_ban_auto_expiration():
    bm = BanManager()
    ip = "198.51.100.58"

    # Ban with -1 second expiration (already expired)
    now = datetime.now(timezone.utc)
    entry = await bm.ban_ip(ip, duration_seconds=10)
    entry.expires_at = now - timedelta(seconds=1)

    # is_banned should detect expiration and evict
    banned, _ = await bm.is_banned(ip)
    assert banned is False
