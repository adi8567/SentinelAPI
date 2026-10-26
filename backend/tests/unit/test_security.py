"""Unit Tests for Security and Authentication."""

import pytest
from backend.app.core.config import settings
from backend.app.core.security import Role, verify_api_key_constant_time


def test_constant_time_comparison():
    key_a = "secret_key_123456789"
    key_b = "secret_key_123456789"
    key_c = "different_key_987654"

    assert verify_api_key_constant_time(key_a, key_b) is True
    assert verify_api_key_constant_time(key_a, key_c) is False


def test_role_hierarchy():
    from backend.app.core.security import AuthenticatedPrincipal

    admin = AuthenticatedPrincipal("admin_user", Role.ADMIN, "api_key")
    agent = AuthenticatedPrincipal("agent_nginx", Role.INGESTION_AGENT, "api_key")
    reader = AuthenticatedPrincipal("reader_1", Role.READONLY, "api_key")

    # Admin satisfies all roles
    assert admin.has_role(Role.ADMIN) is True
    assert admin.has_role(Role.INGESTION_AGENT) is True
    assert admin.has_role(Role.READONLY) is True

    # Agent satisfies only agent
    assert agent.has_role(Role.ADMIN) is False
    assert agent.has_role(Role.INGESTION_AGENT) is True

    # Reader satisfies only reader
    assert reader.has_role(Role.ADMIN) is False
    assert reader.has_role(Role.READONLY) is True
