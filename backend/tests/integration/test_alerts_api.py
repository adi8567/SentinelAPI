"""Integration tests for Security Alerts & Incidents APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_alerts_lifecycle_and_mitigation(async_client: AsyncClient):
    # Ingest an attack to trigger an anomaly
    payload = {
        "source_type": "auto",
        "logs": [
            '203.0.113.210 - - [25/Oct/2026:11:00:20 +0000] "GET /api/v1/products?search=shoes%27%20OR%20%271%27=%271 HTTP/1.1" 400 210 "-" "sqlmap/1.7"',
        ]
    }
    await async_client.post("/api/v1/ingest/raw", json=payload)

    # 1. Query alerts list
    list_resp = await async_client.get("/api/v1/alerts")
    assert list_resp.status_code == 200
    alerts = list_resp.json()
    assert len(alerts) >= 1

    alert_id = alerts[0]["alert_id"]

    # 2. Query single alert details
    get_resp = await async_client.get(f"/api/v1/alerts/{alert_id}")
    assert get_resp.status_code == 200
    alert_data = get_resp.json()
    assert alert_data["alert_id"] == alert_id
    assert alert_data["status"] == "new"

    # 3. Update alert (assign and add note)
    patch_payload = {
        "status": "investigating",
        "assignee": "analyst_sarah",
        "note": "Reviewing payload patterns for potential SQL injection.",
    }
    patch_resp = await async_client.patch(f"/api/v1/alerts/{alert_id}", json=patch_payload)
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["status"] == "investigating"
    assert updated["assignee"] == "analyst_sarah"
    assert len(updated["notes"]) >= 1

    # 4. Mitigate alert (trigger IP block)
    mitigate_payload = {
        "action": "block",
        "ban_duration_seconds": 1800,
        "reason": "Confirmed SQL injection exploit",
    }
    mit_resp = await async_client.post(f"/api/v1/alerts/{alert_id}/mitigate", json=mitigate_payload)
    assert mit_resp.status_code == 200
    mit_data = mit_resp.json()
    assert mit_data["status"] == "mitigated"
    assert mit_data["mitigation_action"] == "block"

    # 5. Mark as false positive
    fp_resp = await async_client.post(
        f"/api/v1/alerts/{alert_id}/false-positive",
        json={"reason": "Penetration testing window authorized"},
    )
    assert fp_resp.status_code == 200
    fp_data = fp_resp.json()
    assert fp_data["status"] == "false_positive"
