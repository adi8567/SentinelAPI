"""Integration Tests for Adaptive Protection & Policy REST APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_and_create_policy(async_client: AsyncClient):
    # 1. List default policies
    resp = await async_client.get("/api/v1/policies")
    assert resp.status_code == 200
    policies = resp.json()
    assert len(policies) >= 5
    policy_ids = [p["policy_id"] for p in policies]
    assert "pol_block_critical_attacks" in policy_ids
    assert "pol_throttle_brute_force" in policy_ids

    # 2. Create custom policy
    new_policy = {
        "policy_id": "pol_custom_test_block",
        "name": "Custom Test Block Rule",
        "description": "Block all access to /admin endpoints",
        "is_enabled": True,
        "priority": 15,
        "conditions": {
            "endpoint_pattern": "^/api/v1/admin",
            "min_risk_score": 40.0,
        },
        "action": "block",
        "action_params": {
            "ban_duration_seconds": 600,
        },
    }
    create_resp = await async_client.post("/api/v1/policies", json=new_policy)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["policy_id"] == "pol_custom_test_block"
    assert created["priority"] == 15

    # 3. Retrieve specific policy
    get_resp = await async_client.get("/api/v1/policies/pol_custom_test_block")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Custom Test Block Rule"

    # 4. Clean up / delete policy
    del_resp = await async_client.delete("/api/v1/policies/pol_custom_test_block")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_blocklist_management_endpoints(async_client: AsyncClient):
    test_ip = "198.51.100.222"

    # 1. Manual IP ban
    ban_payload = {
        "ip": test_ip,
        "duration_seconds": 1800,
        "reason": "Integration test ban",
    }
    ban_resp = await async_client.post("/api/v1/policies/blocklist", json=ban_payload)
    assert ban_resp.status_code == 201
    ban_data = ban_resp.json()
    assert ban_data["ip"] == test_ip
    assert ban_data["is_active"] is True

    # 2. Query blocklist
    list_resp = await async_client.get("/api/v1/policies/blocklist")
    assert list_resp.status_code == 200
    banned_ips = [b["ip"] for b in list_resp.json()]
    assert test_ip in banned_ips

    # 3. Unban
    unban_resp = await async_client.delete(f"/api/v1/policies/blocklist/{test_ip}")
    assert unban_resp.status_code == 200
    assert unban_resp.json()["status"] == "success"

    # 4. Verify unbanned
    list_after = await async_client.get("/api/v1/policies/blocklist")
    banned_after = [b["ip"] for b in list_after.json()]
    assert test_ip not in banned_after


@pytest.mark.asyncio
async def test_quarantine_management_endpoints(async_client: AsyncClient):
    test_ip = "203.0.113.199"

    # 1. Manual Quarantine
    q_payload = {
        "client_ip": test_ip,
        "reason": "Test quarantine isolation",
    }
    q_resp = await async_client.post("/api/v1/policies/quarantine", json=q_payload)
    assert q_resp.status_code == 201
    q_data = q_resp.json()
    assert q_data["client_ip"] == test_ip

    # 2. List Quarantine
    list_resp = await async_client.get("/api/v1/policies/quarantine")
    assert list_resp.status_code == 200
    q_ips = [q["client_ip"] for q in list_resp.json()]
    assert test_ip in q_ips

    # 3. Release Quarantine
    del_resp = await async_client.delete(f"/api/v1/policies/quarantine/{test_ip}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_policy_dry_run_evaluate_and_stats(async_client: AsyncClient):
    # Dry-run evaluation of attack probe
    eval_req = {
        "client_ip": "198.51.100.77",
        "endpoint": "/api/v1/products?id=1%27%20OR%201=1",
        "http_method": "GET",
        "risk_score": 85.0,
        "severity": "critical",
        "attack_types": ["sqli"],
    }
    eval_resp = await async_client.post("/api/v1/policies/evaluate", json=eval_req)
    assert eval_resp.status_code == 200
    result = eval_resp.json()
    assert result["action"] == "block"
    assert result["matched_policy_id"] == "pol_block_critical_attacks"
    assert result["applied_in_dry_run"] is True

    # Policy operational statistics
    stats_resp = await async_client.get("/api/v1/policies/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_policies"] >= 5
    assert stats["enabled_policies"] >= 5
    assert "actions_breakdown" in stats
