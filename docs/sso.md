# SSO Integration Guide

SnabAgent supports Single Sign-On via **SAML 2.0** and **OAuth2/OIDC** (Authorization Code Flow with PKCE).

## Supported Identity Providers

| Provider | Protocol | Status |
|----------|----------|--------|
| Azure Active Directory | OAuth2/OIDC | Supported |
| Keycloak | OAuth2/OIDC + SAML | Supported |
| ADFS | SAML 2.0 | Supported |
| Okta | OAuth2/OIDC | Planned |

## OAuth2/OIDC Setup

### Azure AD

1. Register app in Azure Portal → App Registrations
2. Set redirect URI: `https://your-domain/api/v1/auth/sso/oauth2/azure_ad/callback`
3. Note `Client ID` and `Tenant ID`
4. Create client secret (Certificates & Secrets)
5. Configure in `.env`:

```env
AZURE_AD_CLIENT_ID=<your-client-id>
AZURE_AD_CLIENT_SECRET=<your-secret>
AZURE_AD_TENANT_ID=<your-tenant-id>
```

### Keycloak

1. Create realm and client in Keycloak admin
2. Set Access Type: `confidential`
3. Set Valid Redirect URIs: `https://your-domain/api/v1/auth/sso/oauth2/keycloak/callback`
4. Configure in `.env`:

```env
KEYCLOAK_SERVER_URL=https://keycloak.your-domain.com
KEYCLOAK_REALM=snabagent
KEYCLOAK_CLIENT_ID=snabagent
KEYCLOAK_CLIENT_SECRET=<your-secret>
```

## SAML 2.0 Setup

### Endpoints

| Endpoint | URL |
|----------|-----|
| Login (SP-initiated) | `GET /api/v1/auth/sso/saml/login` |
| ACS (Assertion Consumer) | `POST /api/v1/auth/sso/saml/acs` |
| Metadata | `GET /api/v1/auth/sso/saml/metadata` |

### Configuration

```env
SAML_ENTITY_ID=https://your-domain/api/v1/auth/sso/saml
SAML_IDP_METADATA_URL=https://idp.your-domain.com/metadata
SAML_CERT_PATH=/etc/snabagent/saml/sp.crt
SAML_KEY_PATH=/etc/snabagent/saml/sp.key
```

## User Mapping

SSO users are automatically mapped to SnabAgent users:
- Email from IdP → `User.email`
- Groups/roles from IdP → `User.role` (configurable mapping)
- Organization from IdP → `Customer` (tenant isolation)

First-time SSO users are created with `buyer` role by default.
Admin can change roles via API or Streamlit admin page.

## Security Considerations

- All SSO communications use HTTPS/TLS
- PKCE is enforced for OAuth2 flows
- SAML assertions are validated against IdP certificate
- Session tokens follow the same JWT lifecycle (15min access + 7d refresh)
