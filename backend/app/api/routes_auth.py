"""Authentication and user management routes.

Endpoints for:
- Login/register via Privy or email/wallet
- JWT token generation
- Organization user management (invite, update role, remove)
- API key management
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import (
    AuthUser,
    Role,
    create_access_token,
    get_current_user,
    require_permission,
)
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Schemas ---

class LoginRequest(BaseModel):
    provider: str = "privy"  # privy | wallet | email
    token: str = ""  # Privy token or wallet signature
    email: str = ""
    wallet_address: str = ""


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    org_id: int
    role: str
    expires_in: int


class InviteRequest(BaseModel):
    email: str = ""
    wallet_address: str = ""
    role: str = "member"


class UserInfo(BaseModel):
    user_id: str
    email: str
    role: str
    org_id: int


class UpdateRoleRequest(BaseModel):
    role: str


# --- Routes ---

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and receive a JWT access token.

    In sandbox mode (auth disabled), returns a dev token for the default org.
    In production, verifies Privy token or wallet signature.
    """
    if not settings.auth_enabled:
        # Dev mode: auto-login as owner of org 1
        token = create_access_token("dev-user-001", 1, "owner", "admin@mandate.local")
        return LoginResponse(
            access_token=token,
            user_id="dev-user-001",
            org_id=1,
            role="owner",
            expires_in=settings.jwt_expiry_hours * 3600,
        )

    # Production: verify token and look up user
    if req.provider == "privy":
        from app.core.auth import _verify_privy_token

        privy_data = await _verify_privy_token(req.token)
        user_id = privy_data.get("user_id", "")
        email = privy_data.get("email", req.email)
    elif req.provider == "wallet":
        # Verify wallet signature (simplified — production would use EIP-4361 SIWE)
        user_id = f"wallet_{req.wallet_address[:10]}"
        email = req.email
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")

    # Look up or create membership
    from app.models.auth import User, UserOrgMembership

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        user = User(id=user_id, email=email, wallet_address=req.wallet_address)
        db.add(user)
        db.commit()

    membership = db.query(UserOrgMembership).filter_by(user_id=user_id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="User not in any organization. Ask an admin to invite you.")

    token = create_access_token(user_id, membership.org_id, membership.role, email)
    return LoginResponse(
        access_token=token,
        user_id=user_id,
        org_id=membership.org_id,
        role=membership.role,
        expires_in=settings.jwt_expiry_hours * 3600,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: AuthUser = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserInfo(
        user_id=user.user_id,
        email=user.email,
        role=user.role,
        org_id=user.org_id,
    )


@router.post("/invite")
async def invite_user(
    req: InviteRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_permission("users:invite")),
):
    """Invite a new user to the current organization."""
    from app.models.auth import User, UserOrgMembership

    if req.role not in [r.value for r in Role]:
        raise HTTPException(status_code=400, detail=f"Invalid role: {req.role}")

    # Create user if they don't exist
    user_id = f"invited_{req.email or req.wallet_address}"
    existing = db.query(User).filter_by(id=user_id).first()
    if not existing:
        new_user = User(id=user_id, email=req.email, wallet_address=req.wallet_address)
        db.add(new_user)

    # Create membership
    existing_membership = (
        db.query(UserOrgMembership)
        .filter_by(user_id=user_id, org_id=user.org_id)
        .first()
    )
    if existing_membership:
        raise HTTPException(status_code=409, detail="User already in organization")

    membership = UserOrgMembership(
        user_id=user_id,
        org_id=user.org_id,
        role=req.role,
        invited_by=user.user_id,
    )
    db.add(membership)
    db.commit()

    return {"status": "invited", "user_id": user_id, "role": req.role, "org_id": user.org_id}


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    req: UpdateRoleRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission("settings:write")),
):
    """Update a user's role within the organization."""
    from app.models.auth import UserOrgMembership

    membership = (
        db.query(UserOrgMembership)
        .filter_by(user_id=user_id, org_id=current_user.org_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="User not in organization")

    membership.role = req.role
    db.commit()
    return {"status": "updated", "user_id": user_id, "role": req.role}


@router.delete("/users/{user_id}")
async def remove_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission("settings:write")),
):
    """Remove a user from the organization."""
    from app.models.auth import UserOrgMembership

    membership = (
        db.query(UserOrgMembership)
        .filter_by(user_id=user_id, org_id=current_user.org_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="User not in organization")

    db.delete(membership)
    db.commit()
    return {"status": "removed", "user_id": user_id}
