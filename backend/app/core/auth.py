"""Authentication & authorization middleware.

Supports two modes:
- Disabled (default for dev/sandbox): all requests pass through, org_id from URL.
- Enabled (production): JWT/Privy verification, RBAC, tenant isolation.

Enable via MANDATE_AUTH_ENABLED=true in environment.
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Optional

import hashlib
import hmac

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    AGENT = "agent"


# Permission matrix: which roles can perform which actions
ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.OWNER: {"*"},  # everything
    Role.ADMIN: {
        "treasury:read", "treasury:write",
        "payroll:read", "payroll:write", "payroll:execute",
        "agent:read", "agent:write", "agent:execute",
        "ledger:read", "ledger:write",
        "reports:read", "reports:export",
        "settings:read", "settings:write",
        "users:read", "users:invite",
    },
    Role.MEMBER: {
        "treasury:read",
        "payroll:read", "payroll:write",
        "agent:read", "agent:execute",
        "ledger:read",
        "reports:read", "reports:export",
    },
    Role.VIEWER: {
        "treasury:read",
        "payroll:read",
        "ledger:read",
        "reports:read",
    },
    Role.AGENT: {
        "treasury:read", "treasury:write",
        "payroll:read", "payroll:write", "payroll:execute",
        "agent:read", "agent:write", "agent:execute",
        "ledger:read", "ledger:write",
    },
}


class AuthUser:
    """Authenticated user context injected into request handlers."""

    def __init__(
        self,
        user_id: str,
        org_id: int,
        role: Role,
        email: str = "",
        wallet_address: str = "",
    ):
        self.user_id = user_id
        self.org_id = org_id
        self.role = role
        self.email = email
        self.wallet_address = wallet_address

    def has_permission(self, permission: str) -> bool:
        perms = ROLE_PERMISSIONS.get(self.role, set())
        return "*" in perms or permission in perms

    def require_permission(self, permission: str) -> None:
        if not self.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{self.role}' lacks permission '{permission}'",
            )


# --- JWT token handling ---

def _encode_jwt(payload: dict) -> str:
    """Minimal JWT encoding (HS256). For production, use PyJWT or python-jose."""
    import base64
    import json

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()
    signing_input = f"{header}.{body}"
    signature = hmac.HMAC(
        settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{body}.{sig_b64}"


def _decode_jwt(token: str) -> dict:
    """Decode and verify JWT (HS256)."""
    import base64
    import json

    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Malformed token")

    header_b64, body_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{body_b64}"

    # Verify signature
    expected_sig = hmac.HMAC(
        settings.jwt_secret.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    # Pad base64
    sig_padded = sig_b64 + "=" * (4 - len(sig_b64) % 4)
    actual_sig = base64.urlsafe_b64decode(sig_padded)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    # Decode body
    body_padded = body_b64 + "=" * (4 - len(body_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(body_padded))

    # Check expiry
    if payload.get("exp", 0) < time.time():
        raise HTTPException(status_code=401, detail="Token expired")

    return payload


def create_access_token(user_id: str, org_id: int, role: str, email: str = "") -> str:
    """Create a signed JWT access token."""
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + settings.jwt_expiry_hours * 3600,
    }
    return _encode_jwt(payload)


# --- Privy verification ---

async def _verify_privy_token(token: str) -> dict:
    """Verify a Privy auth token. In production, calls Privy's /auth/verify endpoint."""
    import httpx

    if not settings.privy_app_id or not settings.privy_app_secret:
        raise HTTPException(status_code=500, detail="Privy not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://auth.privy.io/api/v1/token/verify",
            json={"token": token},
            headers={
                "privy-app-id": settings.privy_app_id,
                "Authorization": f"Basic {settings.privy_app_secret}",
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Privy verification failed")
        return resp.json()


# --- FastAPI Dependencies ---

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    """Extract and verify the current user from the request.

    When auth is disabled (sandbox/dev), returns a default admin user for org 1.
    When enabled, verifies JWT and enforces tenant isolation.
    """
    if not settings.auth_enabled:
        # Dev mode: return default admin for the seeded org
        return AuthUser(
            user_id="dev-user-001",
            org_id=1,
            role=Role.OWNER,
            email="admin@mandate.local",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Try JWT first, then Privy
    try:
        payload = _decode_jwt(token)
        return AuthUser(
            user_id=payload["sub"],
            org_id=payload["org_id"],
            role=Role(payload.get("role", "viewer")),
            email=payload.get("email", ""),
        )
    except (HTTPException, Exception):
        pass

    # Privy fallback
    privy_data = await _verify_privy_token(token)
    user_id = privy_data.get("user_id", privy_data.get("sub", ""))
    # Look up org membership from DB
    from app.models.auth import UserOrgMembership
    membership = db.query(UserOrgMembership).filter_by(user_id=user_id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User not associated with any organization")

    return AuthUser(
        user_id=user_id,
        org_id=membership.org_id,
        role=Role(membership.role),
        email=privy_data.get("email", ""),
        wallet_address=privy_data.get("wallet_address", ""),
    )


def require_permission(permission: str):
    """Dependency factory that checks a specific permission."""

    async def _check(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        user.require_permission(permission)
        return user

    return _check
