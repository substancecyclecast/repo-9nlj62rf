"""OAuth2/OIDC SSO integration with PKCE.

Supports Google, Yandex ID, Azure AD, and Keycloak.
Endpoints:
- GET /api/v1/auth/sso/oauth2/{provider}/login
- GET /api/v1/auth/sso/oauth2/{provider}/callback
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
from base64 import urlsafe_b64encode
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from ...db.models import UserRole
from ...db.repositories import CustomerRepo, UserRepo
from ...db.session import AsyncSessionLocal
from ...settings import settings
from ..security import create_access_token, create_refresh_token, hash_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/sso/oauth2", tags=["sso"])

# Provider configurations
PROVIDERS: dict[str, dict] = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scopes": ["openid", "profile", "email"],
        "client_id_env": "OAUTH_GOOGLE_CLIENT_ID",
        "client_secret_env": "OAUTH_GOOGLE_CLIENT_SECRET",
    },
    "yandex": {
        "authorize_url": "https://oauth.yandex.ru/authorize",
        "token_url": "https://oauth.yandex.ru/token",
        "userinfo_url": "https://login.yandex.ru/info",
        "scopes": ["login:email", "login:info"],
        "client_id_env": "OAUTH_YANDEX_CLIENT_ID",
        "client_secret_env": "OAUTH_YANDEX_CLIENT_SECRET",
    },
    "azure_ad": {
        "authorize_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        "userinfo_url": "https://graph.microsoft.com/v1.0/me",
        "scopes": ["openid", "profile", "email"],
        "client_id_env": "OAUTH_AZURE_CLIENT_ID",
        "client_secret_env": "OAUTH_AZURE_CLIENT_SECRET",
    },
    "keycloak": {
        "authorize_url": "{server_url}/realms/{realm}/protocol/openid-connect/auth",
        "token_url": "{server_url}/realms/{realm}/protocol/openid-connect/token",
        "userinfo_url": "{server_url}/realms/{realm}/protocol/openid-connect/userinfo",
        "scopes": ["openid", "profile", "email"],
        "client_id_env": "OAUTH_KEYCLOAK_CLIENT_ID",
        "client_secret_env": "OAUTH_KEYCLOAK_CLIENT_SECRET",
    },
}

# In-memory state store (use Redis in production cluster)
_state_store: dict[str, dict] = {}


def _get_provider_credentials(provider: str) -> tuple[str, str]:
    """Get OAuth credentials from environment."""
    cfg = PROVIDERS[provider]
    client_id = os.environ.get(cfg["client_id_env"], "")
    client_secret = os.environ.get(cfg["client_secret_env"], "")
    if not client_id or not client_secret:
        raise HTTPException(
            503,
            f"OAuth2 provider '{provider}' not configured. "
            f"Set {cfg['client_id_env']} and {cfg['client_secret_env']} in .env",
        )
    return client_id, client_secret


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge."""
    verifier = secrets.token_urlsafe(64)
    challenge = urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


@router.get("/{provider}/login")
async def oauth2_login(provider: str, request: Request):
    """Initiate OAuth2 Authorization Code Flow with PKCE."""
    if provider not in PROVIDERS:
        raise HTTPException(400, f"Unsupported provider: {provider}. Supported: {list(PROVIDERS.keys())}")

    client_id, _ = _get_provider_credentials(provider)
    cfg = PROVIDERS[provider]

    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _generate_pkce()

    # Store state for verification
    _state_store[state] = {"provider": provider, "code_verifier": code_verifier}

    callback_url = f"{settings.service_public_url}/api/v1/auth/sso/oauth2/{provider}/callback"

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": callback_url,
        "scope": " ".join(cfg["scopes"]),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    authorize_url = cfg["authorize_url"]
    # Handle template URLs (Azure AD tenant)
    if "{tenant_id}" in authorize_url:
        tenant_id = os.environ.get("OAUTH_AZURE_TENANT_ID", "common")
        authorize_url = authorize_url.replace("{tenant_id}", tenant_id)

    return RedirectResponse(f"{authorize_url}?{urlencode(params)}")


@router.get("/{provider}/callback")
async def oauth2_callback(provider: str, code: str = "", state: str = "", error: str = ""):
    """Handle OAuth2 callback from IdP."""
    if provider not in PROVIDERS:
        raise HTTPException(400, f"Unsupported provider: {provider}")

    if error:
        raise HTTPException(400, f"OAuth2 error: {error}")
    if not code:
        raise HTTPException(400, "Missing authorization code")

    # Verify state
    state_data = _state_store.pop(state, None)
    if not state_data or state_data["provider"] != provider:
        raise HTTPException(400, "Invalid or expired state parameter")

    client_id, client_secret = _get_provider_credentials(provider)
    cfg = PROVIDERS[provider]

    callback_url = f"{settings.service_public_url}/api/v1/auth/sso/oauth2/{provider}/callback"
    token_url = cfg["token_url"]
    if "{tenant_id}" in token_url:
        tenant_id = os.environ.get("OAUTH_AZURE_TENANT_ID", "common")
        token_url = token_url.replace("{tenant_id}", tenant_id)

    # Exchange code for tokens
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": callback_url,
                "client_id": client_id,
                "client_secret": client_secret,
                "code_verifier": state_data["code_verifier"],
            },
        )
        if token_resp.status_code != 200:
            logger.error("Token exchange failed: %s", token_resp.text)
            raise HTTPException(502, "Failed to exchange authorization code")

        tokens = token_resp.json()
        access_token_ext = tokens["access_token"]

        # Get user info
        userinfo_url = cfg["userinfo_url"]
        if "{tenant_id}" in userinfo_url:
            tenant_id = os.environ.get("OAUTH_AZURE_TENANT_ID", "common")
            userinfo_url = userinfo_url.replace("{tenant_id}", tenant_id)

        headers = {"Authorization": f"Bearer {access_token_ext}"}
        # Yandex uses different format
        if provider == "yandex":
            headers = {"Authorization": f"OAuth {access_token_ext}"}

        userinfo_resp = await client.get(userinfo_url, headers=headers)
        if userinfo_resp.status_code != 200:
            logger.error("UserInfo failed: %s", userinfo_resp.text)
            raise HTTPException(502, "Failed to get user information")

        userinfo = userinfo_resp.json()

    # Extract user fields per provider
    email = _extract_email(provider, userinfo)
    full_name = _extract_name(provider, userinfo)

    if not email:
        raise HTTPException(400, "Could not determine email from SSO provider")

    # Find or create user
    async with AsyncSessionLocal() as session:
        user_repo = UserRepo(session)
        user = await user_repo.by_email(email)

        if not user:
            # Auto-create user with SSO
            customer = await CustomerRepo(session).get_or_create(f"sso_{provider}_{email.split('@')[0]}")
            from ...db.models import User

            user = User(
                email=email.lower(),
                hashed_password=hash_password(secrets.token_urlsafe(32)),
                full_name=full_name,
                customer_id=customer.id,
                role=UserRole.buyer,
                is_active=True,
                email_verified=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

    # Generate SnabAgent JWT
    jwt_access = create_access_token({
        "sub": str(user.id),
        "customer_id": str(user.customer_id) if user.customer_id else None,
        "role": user.role.value,
        "email": user.email,
        "sso_provider": provider,
    })
    jwt_refresh = create_refresh_token(str(user.id))

    # Redirect to frontend with tokens
    frontend_url = settings.frontend_url
    return RedirectResponse(
        f"{frontend_url}/sso/callback?access_token={jwt_access}&refresh_token={jwt_refresh}"
    )


def _extract_email(provider: str, userinfo: dict) -> str:
    """Extract email from provider-specific userinfo."""
    if provider == "yandex":
        return userinfo.get("default_email", userinfo.get("emails", [""])[0] if userinfo.get("emails") else "")
    return userinfo.get("email", "")


def _extract_name(provider: str, userinfo: dict) -> str:
    """Extract full name from provider-specific userinfo."""
    if provider == "yandex":
        return userinfo.get("real_name", userinfo.get("display_name", ""))
    if provider == "azure_ad":
        return userinfo.get("displayName", "")
    return userinfo.get("name", "")
