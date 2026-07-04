"""SAML 2.0 SSO integration.

Provides endpoints for SAML-based Single Sign-On (AD FS, Keycloak, etc.):
- GET  /api/v1/auth/sso/saml/login    — redirect to IdP
- POST /api/v1/auth/sso/saml/acs      — Assertion Consumer Service
- GET  /api/v1/auth/sso/saml/metadata — SP metadata XML
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import UTC, datetime
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response

from ...db.models import UserRole
from ...db.repositories import CustomerRepo, UserRepo
from ...db.session import AsyncSessionLocal
from ...settings import settings
from ..security import create_access_token, create_refresh_token, hash_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/sso/saml", tags=["sso"])

# SAML config from environment
SAML_IDP_SSO_URL = os.environ.get("SAML_IDP_SSO_URL", "")
SAML_IDP_ENTITY_ID = os.environ.get("SAML_IDP_ENTITY_ID", "")
SAML_IDP_CERT = os.environ.get("SAML_IDP_CERT", "")
SAML_SP_ENTITY_ID = os.environ.get("SAML_SP_ENTITY_ID", f"{settings.service_public_url}/api/v1/auth/sso/saml/metadata")
SAML_SP_ACS_URL = os.environ.get("SAML_SP_ACS_URL", f"{settings.service_public_url}/api/v1/auth/sso/saml/acs")

# Simple in-memory request ID tracking
_pending_requests: dict[str, dict] = {}


@router.get("/login")
async def saml_login(request: Request):
    """Redirect user to SAML IdP for authentication."""
    if not SAML_IDP_SSO_URL:
        raise HTTPException(
            503,
            "SAML not configured. Set SAML_IDP_SSO_URL, SAML_IDP_ENTITY_ID, SAML_IDP_CERT in .env",
        )

    request_id = f"_snabagent_{secrets.token_hex(16)}"
    issue_instant = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build AuthnRequest XML
    authn_request = f"""<samlp:AuthnRequest
        xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
        xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
        ID="{request_id}"
        Version="2.0"
        IssueInstant="{issue_instant}"
        Destination="{SAML_IDP_SSO_URL}"
        AssertionConsumerServiceURL="{SAML_SP_ACS_URL}"
        ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
        <saml:Issuer>{SAML_SP_ENTITY_ID}</saml:Issuer>
        <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress" AllowCreate="true"/>
    </samlp:AuthnRequest>"""

    _pending_requests[request_id] = {"created": issue_instant}

    # Base64 encode and deflate for HTTP-Redirect binding
    import base64
    import zlib

    deflated = zlib.compress(authn_request.encode())[2:-4]
    encoded = base64.b64encode(deflated).decode()

    params = {"SAMLRequest": encoded, "RelayState": settings.frontend_url}
    redirect_url = f"{SAML_IDP_SSO_URL}?{urlencode(params)}"

    return RedirectResponse(redirect_url)


@router.post("/acs")
async def saml_acs(request: Request):
    """SAML Assertion Consumer Service — receives SAML response from IdP."""
    if not SAML_IDP_SSO_URL:
        raise HTTPException(503, "SAML not configured")

    form_data = await request.form()
    saml_response_b64 = form_data.get("SAMLResponse", "")
    relay_state = form_data.get("RelayState", settings.frontend_url)

    if not saml_response_b64:
        raise HTTPException(400, "Missing SAMLResponse")

    import base64

    try:
        saml_xml = base64.b64decode(saml_response_b64)
    except Exception:
        raise HTTPException(400, "Invalid SAMLResponse encoding")

    # Parse SAML response (simplified — production should use xmlsec for signature validation)
    try:
        root = ET.fromstring(saml_xml)
    except ET.ParseError:
        raise HTTPException(400, "Invalid SAML XML")

    # Extract NameID (email) from assertion
    ns = {
        "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    }

    status_code = root.find(".//samlp:StatusCode", ns)
    if status_code is not None:
        status_value = status_code.get("Value", "")
        if "Success" not in status_value:
            raise HTTPException(400, f"SAML authentication failed: {status_value}")

    name_id_elem = root.find(".//saml:NameID", ns)
    if name_id_elem is None or not name_id_elem.text:
        raise HTTPException(400, "No NameID (email) found in SAML assertion")

    email = name_id_elem.text.strip().lower()

    # Extract attributes (name, etc.)
    full_name = ""
    attrs = root.findall(".//saml:Attribute", ns)
    for attr in attrs:
        attr_name = attr.get("Name", "")
        value_elem = attr.find("saml:AttributeValue", ns)
        if value_elem is not None and value_elem.text:
            if "displayname" in attr_name.lower() or "name" in attr_name.lower():
                full_name = value_elem.text

    # Find or create user
    async with AsyncSessionLocal() as session:
        user_repo = UserRepo(session)
        user = await user_repo.by_email(email)

        if not user:
            customer = await CustomerRepo(session).get_or_create(f"saml_{email.split('@')[1]}")
            from ...db.models import User

            user = User(
                email=email,
                hashed_password=hash_password(secrets.token_urlsafe(32)),
                full_name=full_name or email.split("@")[0],
                customer_id=customer.id,
                role=UserRole.buyer,
                is_active=True,
                email_verified=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

    # Generate JWT tokens
    jwt_access = create_access_token({
        "sub": str(user.id),
        "customer_id": str(user.customer_id) if user.customer_id else None,
        "role": user.role.value,
        "email": user.email,
        "sso_provider": "saml",
    })
    jwt_refresh = create_refresh_token(str(user.id))

    frontend_url = relay_state or settings.frontend_url
    return RedirectResponse(
        f"{frontend_url}/sso/callback?access_token={jwt_access}&refresh_token={jwt_refresh}"
    )


@router.get("/metadata")
async def saml_metadata():
    """Return SP metadata XML for IdP configuration."""
    metadata = f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{SAML_SP_ENTITY_ID}">
    <md:SPSSODescriptor
        AuthnRequestsSigned="false"
        WantAssertionsSigned="true"
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{SAML_SP_ACS_URL}"
            index="0"
            isDefault="true"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>"""
    return Response(content=metadata, media_type="application/xml")
