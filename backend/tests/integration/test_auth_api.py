"""Integration tests for Authentication & Identity REST endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_login_and_token_refresh(async_client: AsyncClient):
    # 1. Login with valid credentials
    login_payload = {
        "username": "admin",
        "password": "SentinelAdmin#2026!",
    }
    resp = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert resp.status_code == 200
    token_data = resp.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "Bearer"
    assert token_data["username"] == "admin"
    assert token_data["role"] == "admin"

    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]

    # 2. Check /auth/me with Bearer JWT
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["identifier"] == "admin"
    assert me_data["role"] == "admin"
    assert "read:dashboard" in me_data["permissions"]

    # 3. Refresh token exchange
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    assert new_tokens["access_token"] != access_token


@pytest.mark.asyncio
async def test_auth_login_invalid_credentials(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401
    assert "Incorrect username or password" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_admin_provision_api_key(async_client: AsyncClient):
    # Admin creates agent API key
    key_payload = {
        "name": "Integration-Test-Agent",
        "role": "ingestion_agent",
        "expires_in_days": 7,
    }
    create_resp = await async_client.post("/api/v1/auth/api-keys", json=key_payload)
    assert create_resp.status_code == 201
    key_data = create_resp.json()
    assert "key_id" in key_data
    assert key_data["raw_key"] is not None
    assert key_data["raw_key"].startswith("sk_live_")

    # List API keys
    list_resp = await async_client.get("/api/v1/auth/api-keys")
    assert list_resp.status_code == 200
    keys = list_resp.json()
    assert any(k["name"] == "Integration-Test-Agent" for k in keys)

    # Revoke key
    key_id = key_data["key_id"]
    del_resp = await async_client.delete(f"/api/v1/auth/api-keys/{key_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"
