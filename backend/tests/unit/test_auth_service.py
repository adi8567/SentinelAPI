"""Unit tests for AuthService: PBKDF2 password hashing, JWT tokens, and API keys."""

from datetime import timedelta
import pytest
from backend.app.schemas.auth import ApiKeyCreate, UserCreate, UserRole
from backend.app.services.auth.auth_service import AuthService


@pytest.fixture
async def auth_svc():
    svc = AuthService()
    await svc.initialize()
    return svc


def test_password_hashing(auth_svc):
    password = "SuperSecurePassword123!"
    hashed = auth_svc.hash_password(password)

    assert hashed.startswith("pbkdf2_sha256$100000$")
    # Verify correct password
    assert auth_svc.verify_password(password, hashed) is True
    # Verify incorrect password fails
    assert auth_svc.verify_password("WrongPassword!", hashed) is False


def test_jwt_token_lifecycle(auth_svc):
    data = {"sub": "test_user", "role": "analyst", "type": "access"}
    token = auth_svc.create_jwt_token(data, expires_delta=timedelta(minutes=15))
    assert isinstance(token, str)

    payload = auth_svc.decode_jwt_token(token)
    assert payload["sub"] == "test_user"
    assert payload["role"] == "analyst"
    assert payload["iss"] == "sentinelapi"


@pytest.mark.asyncio
async def test_user_authentication_flow(auth_svc):
    # Verify seeded admin
    admin = await auth_svc.authenticate_user("admin", "SentinelAdmin#2026!")
    assert admin is not None
    assert admin.username == "admin"
    assert admin.role == UserRole.ADMIN

    # Verify invalid credentials
    invalid = await auth_svc.authenticate_user("admin", "WrongPass123!")
    assert invalid is None

    # Create new user
    new_user_req = UserCreate(
        username="secops_john",
        email="john@sentinelapi.local",
        full_name="John Doe",
        password="MySecretPassword99!",
        role=UserRole.OPERATOR,
    )
    created = await auth_svc.create_user(new_user_req)
    assert created.username == "secops_john"
    assert created.role == UserRole.OPERATOR

    # Authenticate newly created user
    auth_john = await auth_svc.authenticate_user("secops_john", "MySecretPassword99!")
    assert auth_john is not None


@pytest.mark.asyncio
async def test_api_key_lifecycle(auth_svc):
    key_req = ApiKeyCreate(
        name="Envoy-Edge-Gateway",
        role=UserRole.GATEWAY_AGENT,
        expires_in_days=30,
    )
    raw_key, record = await auth_svc.generate_api_key(key_req)
    assert raw_key.startswith("sk_live_")
    assert record.is_active is True
    assert record.role == UserRole.GATEWAY_AGENT

    # Verify valid API key
    verified = await auth_svc.verify_api_key(raw_key)
    assert verified is not None
    assert verified.name == "Envoy-Edge-Gateway"

    # Verify bogus API key
    bogus = await auth_svc.verify_api_key("sk_live_bogus_token_123")
    assert bogus is None

    # Revoke API key
    revoked = await auth_svc.revoke_api_key(record.key_id)
    assert revoked is True
    assert (await auth_svc.verify_api_key(raw_key)) is None
