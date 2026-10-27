"""Unit tests for quarantine isolation manager."""

import pytest
from backend.app.services.policy.actions.quarantine_manager import QuarantineManager


@pytest.mark.asyncio
async def test_quarantine_lifecycle():
    qm = QuarantineManager()
    client_ip = "203.0.113.88"

    # 1. Enact quarantine
    entry = await qm.quarantine(client_ip, client_id="user_suspicious_1", reason="Anomalous sequence")
    assert entry.client_ip == client_ip
    assert entry.client_id == "user_suspicious_1"
    assert entry.is_active is True

    # 2. Check quarantine
    is_q, q_rec = await qm.is_quarantined(client_ip)
    assert is_q is True
    assert q_rec.client_ip == client_ip

    # 3. List active
    active = await qm.list_active()
    assert len(active) == 1
    assert active[0].client_ip == client_ip

    # 4. Release
    released = await qm.release(client_ip)
    assert released is True
    assert (await qm.is_quarantined(client_ip))[0] is False
    assert (await qm.count_active()) == 0
