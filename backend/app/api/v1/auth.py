"""SentinelAPI Authentication and User Management Endpoints.

Provides login, token refresh, user profile, and API key provisioning APIs.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.api.deps import CurrentPrincipal
from backend.app.core.security import AuthenticatedPrincipal, Role, require_role
from backend.app.schemas.auth import (
    ApiKeyCreate,
    ApiKeyRecord,
    ApiKeyResponse,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from backend.app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    """Authenticates username and password and returns JWT access and refresh tokens."""
    user = await auth_service.authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_service.create_user_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshTokenRequest) -> TokenResponse:
    """Exchanges a valid refresh token for a new access and refresh token pair."""
    try:
        payload = auth_service.decode_jwt_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type: expected refresh token.",
            )
        user_id = payload.get("user_id")
        user = await auth_service.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or deactivated.",
            )
        return auth_service.create_user_tokens(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired refresh token: {e}",
        )


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_profile(
    principal: CurrentPrincipal,
) -> Dict[str, Any]:
    """Retrieves profile and RBAC permissions for the currently authenticated principal."""
    user = await auth_service.get_user_by_username(principal.identifier)
    return {
        "identifier": principal.identifier,
        "role": principal.role.value,
        "auth_method": principal.auth_method,
        "permissions": [p.value for p in principal.permissions],
        "email": user.email if user else None,
        "full_name": user.full_name if user else principal.identifier,
    }


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: UserCreate,
    principal: AuthenticatedPrincipal = Depends(require_role(Role.ADMIN)),
) -> UserResponse:
    """Creates a new user account with designated role (Admin only)."""
    try:
        user = await auth_service.create_user(req)
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def generate_api_key(
    req: ApiKeyCreate,
    principal: AuthenticatedPrincipal = Depends(require_role(Role.ADMIN)),
) -> ApiKeyResponse:
    """Generates a secure API key for ingestion agents or external integrations (Admin only).
    Note: The plaintext raw_key is only returned once in this response!
    """
    raw_key, rec = await auth_service.generate_api_key(req)
    return ApiKeyResponse(
        key_id=rec.key_id,
        name=rec.name,
        prefix=rec.prefix,
        raw_key=raw_key,
        role=rec.role,
        created_at=rec.created_at,
        expires_at=rec.expires_at,
        last_used_at=rec.last_used_at,
        is_active=rec.is_active,
    )


@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    principal: AuthenticatedPrincipal = Depends(require_role(Role.ADMIN)),
) -> List[ApiKeyResponse]:
    """Lists all registered API keys (without revealing plaintext secrets)."""
    records = await auth_service.list_api_keys()
    return [
        ApiKeyResponse(
            key_id=r.key_id,
            name=r.name,
            prefix=r.prefix,
            raw_key=None,
            role=r.role,
            created_at=r.created_at,
            expires_at=r.expires_at,
            last_used_at=r.last_used_at,
            is_active=r.is_active,
        )
        for r in records
    ]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_200_OK)
async def revoke_api_key(
    key_id: str,
    principal: AuthenticatedPrincipal = Depends(require_role(Role.ADMIN)),
) -> Dict[str, Any]:
    """Revokes an API key (Admin only)."""
    revoked = await auth_service.revoke_api_key(key_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key '{key_id}' not found.",
        )
    return {"status": "success", "revoked_key_id": key_id}
