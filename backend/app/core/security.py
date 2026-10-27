"""SentinelAPI Security Module.

Provides authentication, authorization (RBAC), constant-time API key
validation, JWT token verification, and security headers.
"""

from enum import Enum
import hmac
import logging
import secrets
from typing import List, Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
import jwt
from backend.app.core.config import settings
from backend.app.schemas.auth import Permission, ROLE_PERMISSIONS, UserRole

logger = logging.getLogger("sentinelapi.security")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)


class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    ANALYST = "analyst"
    AUDITOR = "auditor"
    INGESTION_AGENT = "ingestion_agent"
    READONLY = "readonly"


class AuthenticatedPrincipal:
    """Represents an authenticated client or user identity with RBAC permissions."""

    def __init__(
        self,
        identifier: str,
        role: Role,
        auth_method: str,
        permissions: Optional[List[Permission]] = None,
        user_id: Optional[str] = None,
    ):
        self.identifier = identifier
        self.role = role
        self.auth_method = auth_method
        self.user_id = user_id or identifier

        # Determine permissions from role if not explicitly provided
        if permissions is not None:
            self.permissions = permissions
        else:
            mapped_role = UserRole(self.role.value) if self.role.value in [r.value for r in UserRole] else UserRole.ANALYST
            self.permissions = ROLE_PERMISSIONS.get(mapped_role, [])

    def has_role(self, required_role: Role) -> bool:
        if self.role == Role.ADMIN:
            return True
        return self.role == required_role

    def has_permission(self, required_permission: Permission) -> bool:
        if self.role == Role.ADMIN:
            return True
        return required_permission in self.permissions

    def __repr__(self) -> str:
        return f"Principal({self.identifier}, role={self.role.value}, via={self.auth_method})"


def verify_api_key_constant_time(provided_key: str, candidate_key: str) -> bool:
    """Performs constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(provided_key.encode("utf-8"), candidate_key.encode("utf-8"))


async def get_current_principal(
    api_key: Optional[str] = Security(api_key_header),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(bearer_auth),
) -> AuthenticatedPrincipal:
    """Authenticates the incoming request using either X-API-Key header, JWT Bearer token, or API key Bearer.
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
            detail="Missing required authentication: Provide 'X-API-Key' header or 'Authorization: Bearer <token>'.",
            headers={"WWW-Authenticate": "ApiKey, Bearer"},
        )

    # 1. Attempt JWT Token Decode (if Bearer token looks like JWT)
    if auth_method == "bearer" and "." in token_to_check:
        try:
            from backend.app.services.auth.auth_service import auth_service
            payload = auth_service.decode_jwt_token(token_to_check)
            username = payload.get("sub", "user")
            role_str = payload.get("role", "analyst")
            role_enum = Role(role_str) if role_str in [r.value for r in Role] else Role.ANALYST
            perms = [Permission(p) for p in payload.get("permissions", []) if p in [pm.value for pm in Permission]]

            return AuthenticatedPrincipal(
                identifier=username,
                role=role_enum,
                auth_method="jwt",
                permissions=perms,
                user_id=payload.get("user_id"),
            )
        except (jwt.PyJWTError, Exception) as e:
            logger.debug(f"Bearer token was not a valid JWT ({e}); falling back to API Key verification.")

    # 2. Check Static Admin API Key (constant time)
    if verify_api_key_constant_time(token_to_check, settings.ADMIN_API_KEY):
        return AuthenticatedPrincipal(identifier="admin", role=Role.ADMIN, auth_method=auth_method)

    # 3. Check Pre-Configured Ingestion API Keys
    for agent_key in settings.INGESTION_API_KEYS:
        if verify_api_key_constant_time(token_to_check, agent_key):
            key_id = f"agent_{token_to_check[-6:]}"
            return AuthenticatedPrincipal(identifier=key_id, role=Role.INGESTION_AGENT, auth_method=auth_method)

    # 4. Check Dynamic API Keys issued via AuthService
    try:
        from backend.app.services.auth.auth_service import auth_service
        key_rec = await auth_service.verify_api_key(token_to_check)
        if key_rec:
            role_enum = Role(key_rec.role.value) if key_rec.role.value in [r.value for r in Role] else Role.INGESTION_AGENT
            return AuthenticatedPrincipal(
                identifier=key_rec.name,
                role=role_enum,
                auth_method="dynamic_api_key",
            )
    except Exception as e:
        logger.error(f"Error checking dynamic API key: {e}")

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


def require_permission(required_permission: Permission):
    """Dependency that enforces granular RBAC permissions."""
    async def permission_checker(
        principal: AuthenticatedPrincipal = Security(get_current_principal)
    ) -> AuthenticatedPrincipal:
        if not principal.has_permission(required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires permission '{required_permission.value}'. Access denied.",
            )
        return principal
    return permission_checker
