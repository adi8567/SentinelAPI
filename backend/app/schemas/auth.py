"""SentinelAPI Authentication and User Schemas.

Data models for JWT tokens, Users, Roles, RBAC permissions, and API Keys.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    ADMIN = "admin"              # Full administrative access
    OPERATOR = "operator"        # Policy enforcement, mitigating alerts, retraining
    ANALYST = "analyst"          # Alert investigation, dashboards, false positives
    AUDITOR = "auditor"          # Read-only access to decisions, compliance, logs
    GATEWAY_AGENT = "ingestion_agent" # Restricted to data ingestion only


class Permission(str, Enum):
    READ_DASHBOARD = "read:dashboard"
    READ_ALERTS = "read:alerts"
    WRITE_ALERTS = "write:alerts"
    READ_INVENTORY = "read:inventory"
    READ_BASELINES = "read:baselines"
    WRITE_POLICIES = "write:policies"
    READ_POLICIES = "read:policies"
    READ_INVESTIGATION = "read:investigation"
    WRITE_INGEST = "write:ingest"
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"


ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.ADMIN: list(Permission),
    UserRole.OPERATOR: [
        Permission.READ_DASHBOARD,
        Permission.READ_ALERTS,
        Permission.WRITE_ALERTS,
        Permission.READ_INVENTORY,
        Permission.READ_BASELINES,
        Permission.READ_POLICIES,
        Permission.WRITE_POLICIES,
        Permission.READ_INVESTIGATION,
        Permission.WRITE_INGEST,
        Permission.ADMIN_SYSTEM,
    ],
    UserRole.ANALYST: [
        Permission.READ_DASHBOARD,
        Permission.READ_ALERTS,
        Permission.WRITE_ALERTS,
        Permission.READ_INVENTORY,
        Permission.READ_BASELINES,
        Permission.READ_POLICIES,
        Permission.READ_INVESTIGATION,
    ],
    UserRole.AUDITOR: [
        Permission.READ_DASHBOARD,
        Permission.READ_ALERTS,
        Permission.READ_INVENTORY,
        Permission.READ_BASELINES,
        Permission.READ_POLICIES,
        Permission.READ_INVESTIGATION,
    ],
    UserRole.GATEWAY_AGENT: [
        Permission.WRITE_INGEST,
    ],
}


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., min_length=6, description="User password")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # seconds
    user_id: str
    username: str
    role: UserRole
    permissions: List[Permission]


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., description="User email address")
    full_name: str
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.ANALYST


class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserInDB(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    full_name: str
    hashed_password: str
    role: UserRole = UserRole.ANALYST
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: Optional[datetime] = None


class ApiKeyCreate(BaseModel):
    name: str = Field(..., description="Description or agent name, e.g. 'Kong-Prod-Gateway'")
    role: UserRole = UserRole.GATEWAY_AGENT
    expires_in_days: Optional[int] = Field(None, description="Expiration in days (None for permanent)")


class ApiKeyRecord(BaseModel):
    key_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    prefix: str = Field(..., description="First 8 characters of key for display (e.g. 'sk_live_...')")
    hashed_key: str
    role: UserRole
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = True


class ApiKeyResponse(BaseModel):
    key_id: str
    name: str
    prefix: str
    raw_key: Optional[str] = Field(None, description="Plaintext key, shown only once upon creation")
    role: UserRole
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool
