"""SentinelAPI Core Authentication & Identity Service.

Handles PBKDF2 password hashing, JWT access & refresh token issuance,
RBAC permission mapping, and API key lifecycle management.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import secrets
from typing import Any, Dict, List, Optional, Tuple
import uuid
import jwt
from backend.app.core.config import settings
from backend.app.schemas.auth import (
    ApiKeyCreate,
    ApiKeyRecord,
    ApiKeyResponse,
    Permission,
    ROLE_PERMISSIONS,
    TokenResponse,
    UserCreate,
    UserInDB,
    UserResponse,
    UserRole,
)

logger = logging.getLogger("sentinelapi.auth")


class AuthService:
    """Manages authentication, token generation, user accounts, and API keys."""

    def __init__(self):
        self._users: Dict[str, UserInDB] = {}  # username -> UserInDB
        self._users_by_id: Dict[str, UserInDB] = {}
        self._api_keys: Dict[str, ApiKeyRecord] = {}  # key_id -> ApiKeyRecord
        self._api_keys_by_hash: Dict[str, ApiKeyRecord] = {}  # hashed_key -> ApiKeyRecord
        self._lock = asyncio.Lock()
        self._initialized = False

    @staticmethod
    def hash_password(password: str) -> str:
        """Secure PBKDF2 HMAC SHA-256 password hashing with random salt."""
        salt = secrets.token_bytes(16)
        iterations = 100_000
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return f"pbkdf2_sha256${iterations}${salt.hex()}${key.hex()}"

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies plaintext password against PBKDF2 hash using constant-time comparison."""
        try:
            parts = hashed_password.split("$")
            if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
                return False
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            expected_key = bytes.fromhex(parts[3])
            actual_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(actual_key, expected_key)
        except Exception:
            return False

    @staticmethod
    def hash_api_key(raw_key: str) -> str:
        """Generates SHA-256 hash of an API key for safe database storage."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def create_jwt_token(self, data: Dict[str, Any], expires_delta: timedelta) -> str:
        """Creates a signed JWT token."""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        to_encode.update({
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + expires_delta,
            "iss": "sentinelapi",
        })
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

    def decode_jwt_token(self, token: str) -> Dict[str, Any]:
        """Decodes and validates a JWT token."""
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            issuer="sentinelapi",
            options={"require": ["exp", "iat", "sub"]},
        )

    def create_user_tokens(self, user: UserInDB) -> TokenResponse:
        """Generates an access token and refresh token pair for an authenticated user."""
        permissions = [p.value for p in ROLE_PERMISSIONS.get(user.role, [])]
        access_payload = {
            "sub": user.username,
            "user_id": user.user_id,
            "role": user.role.value,
            "permissions": permissions,
            "type": "access",
        }
        access_token = self.create_jwt_token(
            access_payload,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        refresh_payload = {
            "sub": user.username,
            "user_id": user.user_id,
            "type": "refresh",
        }
        refresh_token = self.create_jwt_token(
            refresh_payload,
            expires_delta=timedelta(days=7),
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            permissions=ROLE_PERMISSIONS.get(user.role, []),
        )

    async def initialize(self) -> None:
        """Seeds default administrative and operator accounts and agent API keys."""
        if self._initialized:
            return

        async with self._lock:
            # Seed default admin user
            if "admin" not in self._users:
                admin_user = UserInDB(
                    username="admin",
                    email="admin@sentinelapi.local",
                    full_name="Sentinel Administrator",
                    hashed_password=self.hash_password("SentinelAdmin#2026!"),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
                self._users["admin"] = admin_user
                self._users_by_id[admin_user.user_id] = admin_user

            # Seed default security analyst
            if "analyst" not in self._users:
                analyst_user = UserInDB(
                    username="analyst",
                    email="analyst@sentinelapi.local",
                    full_name="SOC Security Analyst",
                    hashed_password=self.hash_password("SentinelAnalyst#2026!"),
                    role=UserRole.ANALYST,
                    is_active=True,
                )
                self._users["analyst"] = analyst_user
                self._users_by_id[analyst_user.user_id] = analyst_user

            # Seed default auditor
            if "auditor" not in self._users:
                auditor_user = UserInDB(
                    username="auditor",
                    email="auditor@sentinelapi.local",
                    full_name="Compliance Auditor",
                    hashed_password=self.hash_password("SentinelAuditor#2026!"),
                    role=UserRole.AUDITOR,
                    is_active=True,
                )
                self._users["auditor"] = auditor_user
                self._users_by_id[auditor_user.user_id] = auditor_user

            # Seed default operator
            if "operator" not in self._users:
                operator_user = UserInDB(
                    username="operator",
                    email="operator@sentinelapi.local",
                    full_name="SecOps Operator",
                    hashed_password=self.hash_password("SentinelOperator#2026!"),
                    role=UserRole.OPERATOR,
                    is_active=True,
                )
                self._users["operator"] = operator_user
                self._users_by_id[operator_user.user_id] = operator_user

            # Seed pre-configured gateway agent API keys
            for key in settings.INGESTION_API_KEYS:
                h = self.hash_api_key(key)
                if h not in self._api_keys_by_hash:
                    prefix = key[:8] if len(key) >= 8 else key
                    rec = ApiKeyRecord(
                        name="Pre-configured Ingestion Agent Key",
                        prefix=prefix,
                        hashed_key=h,
                        role=UserRole.GATEWAY_AGENT,
                        is_active=True,
                    )
                    self._api_keys[rec.key_id] = rec
                    self._api_keys_by_hash[h] = rec

            self._initialized = True
            logger.info("AuthService initialized with default accounts and API keys.")

    async def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        """Validates username and password credentials."""
        if not self._initialized:
            await self.initialize()

        user = self._users.get(username.lower())
        if not user or not user.is_active:
            return None

        if self.verify_password(password, user.hashed_password):
            user.last_login_at = datetime.now(timezone.utc)
            return user
        return None

    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Retrieves a user by username."""
        if not self._initialized:
            await self.initialize()
        return self._users.get(username.lower())

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Retrieves a user by user_id."""
        if not self._initialized:
            await self.initialize()
        return self._users_by_id.get(user_id)

    async def create_user(self, req: UserCreate) -> UserInDB:
        """Creates a new user account."""
        if not self._initialized:
            await self.initialize()

        uname = req.username.lower()
        async with self._lock:
            if uname in self._users:
                raise ValueError(f"Username '{req.username}' already exists.")

            user = UserInDB(
                username=uname,
                email=str(req.email),
                full_name=req.full_name,
                hashed_password=self.hash_password(req.password),
                role=req.role,
                is_active=True,
            )
            self._users[uname] = user
            self._users_by_id[user.user_id] = user
            logger.info(f"Created new user '{uname}' with role '{req.role.value}'.")
            return user

    async def generate_api_key(self, req: ApiKeyCreate) -> Tuple[str, ApiKeyRecord]:
        """Generates a secure API key with secret token returned only once."""
        if not self._initialized:
            await self.initialize()

        raw_secret = f"sk_live_{secrets.token_urlsafe(32)}"
        hashed = self.hash_api_key(raw_secret)
        prefix = raw_secret[:12] + "..."

        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=req.expires_in_days)) if req.expires_in_days else None

        rec = ApiKeyRecord(
            name=req.name,
            prefix=prefix,
            hashed_key=hashed,
            role=req.role,
            created_at=now,
            expires_at=expires_at,
            is_active=True,
        )

        async with self._lock:
            self._api_keys[rec.key_id] = rec
            self._api_keys_by_hash[hashed] = rec

        logger.info(f"Generated new API Key '{req.name}' (Prefix: {prefix}).")
        return raw_secret, rec

    async def verify_api_key(self, raw_key: str) -> Optional[ApiKeyRecord]:
        """Verifies if an API key is valid and not expired."""
        if not self._initialized:
            await self.initialize()

        hashed = self.hash_api_key(raw_key)
        rec = self._api_keys_by_hash.get(hashed)
        if not rec or not rec.is_active:
            return None

        # Check expiration
        if rec.expires_at and datetime.now(timezone.utc) > rec.expires_at:
            rec.is_active = False
            return None

        rec.last_used_at = datetime.now(timezone.utc)
        return rec

    async def list_api_keys(self) -> List[ApiKeyRecord]:
        """Lists all registered API keys."""
        if not self._initialized:
            await self.initialize()
        async with self._lock:
            return list(self._api_keys.values())

    async def revoke_api_key(self, key_id: str) -> bool:
        """Revokes an API key."""
        if not self._initialized:
            await self.initialize()
        async with self._lock:
            rec = self._api_keys.get(key_id)
            if rec:
                rec.is_active = False
                return True
            return False


# Global singleton instance
auth_service = AuthService()
