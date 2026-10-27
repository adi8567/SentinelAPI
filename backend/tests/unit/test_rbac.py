"""Unit tests for RBAC Role hierarchy and granular permissions."""

import pytest
from backend.app.core.security import AuthenticatedPrincipal, Role
from backend.app.schemas.auth import Permission, ROLE_PERMISSIONS, UserRole


def test_admin_has_all_permissions_and_roles():
    admin = AuthenticatedPrincipal(identifier="admin", role=Role.ADMIN, auth_method="jwt")
    # Admin satisfies any role check
    assert admin.has_role(Role.ADMIN) is True
    assert admin.has_role(Role.ANALYST) is True
    assert admin.has_role(Role.OPERATOR) is True
    assert admin.has_role(Role.INGESTION_AGENT) is True

    # Admin satisfies any permission
    for perm in Permission:
        assert admin.has_permission(perm) is True


def test_analyst_permissions():
    analyst = AuthenticatedPrincipal(identifier="analyst", role=Role.ANALYST, auth_method="jwt")
    assert analyst.has_role(Role.ANALYST) is True
    assert analyst.has_role(Role.ADMIN) is False

    # Analyst can read dashboard and alerts
    assert analyst.has_permission(Permission.READ_DASHBOARD) is True
    assert analyst.has_permission(Permission.READ_ALERTS) is True
    assert analyst.has_permission(Permission.READ_INVESTIGATION) is True

    # Analyst cannot write policies or administer users
    assert analyst.has_permission(Permission.WRITE_POLICIES) is False
    assert analyst.has_permission(Permission.ADMIN_USERS) is False


def test_gateway_agent_permissions():
    agent = AuthenticatedPrincipal(identifier="agent_gw", role=Role.INGESTION_AGENT, auth_method="api_key")
    assert agent.has_role(Role.INGESTION_AGENT) is True
    assert agent.has_role(Role.ANALYST) is False
    assert agent.has_permission(Permission.WRITE_INGEST) is True
    assert agent.has_permission(Permission.READ_DASHBOARD) is False
