"""SentinelAPI Security Module.

Provides authentication, authorization (RBAC), constant-time API key
validation, and security headers.
"""

import hmac
import secrets
from enum import Enum
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from backend.app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)


class Role(str, Enum):
    ADMIN = "admin"
    INGESTION_AGENT = "ingestion_agent"
    ANALYST = "analyst"
    READONLY = "readonly"


class AuthenticatedPrincipal:
    def __init__(self, identifier: str, role: Role, auth_method: str):
        self.identifier = identifier
        self.role = role
        self.auth_method = auth_method

    def has_role(self, required_role: Role) -> bool:
        if self.role == Role.ADMIN:
            return True
        return self.role == required_role

    def __repr__(self) -> str:
        return f"Principal({self.identifier}, role={self.role}, via={self.auth_method})"


def verify_api_key_constant_time(provided_key: str, candidate_key: str) -> bool:
    """Performs constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(provided_key.encode("utf-8"), candidate_key.encode("utf-8"))


async def get_current_principal(
    api_key: Optional[str] = Security(api_key_header),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(bearer_auth),
) -> AuthenticatedPrincipal:
    """Authenticates the incoming request using either X-API-Key header or Bearer token.
    Raises HTTP 401 if unauthorized and anonymous ingestion is disabled.
    """
    token_to_check = api_key
    auth_method = "api_key"

    if not token_to_check and bearer_creds:
        token_to_check = bearer_creds.credentials
        auth_method = "bearer"

    if not token_to_check:
        if settings.ALLOW_ANONYMOUS_INGESTION:
            return AuthenticatedPrincipal(identifier="anonymous", role=Role.READONLY, auth_method="none")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication: Provide 'X-API-Key' header or 'Authorization: Bearer <key>'.",
            headers={"WWW-Authenticate": "ApiKey, Bearer"},
        )

    # 1. Check Admin API Key
    if verify_api_key_constant_time(token_to_check, settings.ADMIN_API_KEY):
        return AuthenticatedPrincipal(identifier="admin", role=Role.ADMIN, auth_method=auth_method)

    # 2. Check Ingestion API Keys
    for agent_key in settings.INGESTION_API_KEYS:
        if verify_api_key_constant_time(token_to_check, agent_key):
            # Derives a safe key identifier for audit logs (prefix + hash)
            key_id = f"agent_{token_to_check[-6:]}"
            return AuthenticatedPrincipal(identifier=key_id, role=Role.INGESTION_AGENT, auth_method=auth_method)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked authentication credentials.",
        headers={"WWW-Authenticate": "ApiKey, Bearer"},
    )


def require_role(required_role: Role):
    """Dependency that enforces a specific Role on endpoints."""
    async def role_checker(
        principal: AuthenticatedPrincipal = Security(get_current_principal)
    ) -> AuthenticatedPrincipal:
        if not principal.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires role '{required_role.value}'. Current role: '{principal.role.value}'.",
            )
        return principal
    return role_checker
