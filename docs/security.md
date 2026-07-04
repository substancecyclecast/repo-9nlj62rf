# Security Documentation

## Overview

SnabAgent implements defense-in-depth security measures for enterprise procurement data.

## Authentication & Authorization

### JWT Tokens
- **Access tokens**: 15-minute TTL, HS256 signed
- **Refresh tokens**: 7-day TTL, one-time use rotation
- Secret key validated on startup (must not be "changeme" in production)

### API Keys
- Machine-to-machine authentication via `X-API-Key` header
- Validated on startup (must not be "dev-only-key" in production)

### Password Policy
- Minimum 8 characters
- At least 1 digit
- At least 1 special character
- Passwords hashed with bcrypt (12 rounds)

### Rate Limiting
- Login: 5 attempts/minute per IP (HTTP 429 with Retry-After)
- General API: 100 requests/minute per IP
- Configurable via environment variables

### SSO
- SAML 2.0 and OAuth2/OIDC support
- PKCE enforced for OAuth2 flows
- See `docs/sso.md` for setup

## Security Headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-XSS-Protection: 0` (modern browsers use CSP instead)
- `Referrer-Policy: strict-origin-when-cross-origin`

## Data Protection

### Encryption
- **At rest**: AES-256 (PostgreSQL TDE or volume encryption)
- **In transit**: TLS 1.3 (enforced via Caddy/nginx)
- **Secrets**: Pydantic `SecretStr` prevents accidental logging

### Access Control
- Multi-tenant isolation by `customer_id`
- Role-based access: admin, buyer, viewer
- Buyer approval limits (configurable per user)

### Audit Logging
- Append-only audit log for all lot operations
- Records: agent, step, input/output, confidence, model, latency
- Queryable via API and Streamlit UI

## Compliance

### 152-ФЗ (Personal Data)
- Personal data stored in Russian jurisdiction
- Data retention: 3 years
- Incident notification: 72 hours
- See `docs/legal/DPA.md` for Data Processing Agreement

### Security Scanning
- **SAST**: Bandit (`bandit -r src -ll`)
- **Dependencies**: pip-audit for CVE scanning
- **SBOM**: CycloneDX format (`make sbom`)

## Incident Response

1. **Detection**: Prometheus alerts, error rate monitoring
2. **Containment**: Circuit breaker for LLM, rate limiting
3. **Notification**: 72-hour window for data breach notification
4. **Recovery**: Backup/restore scripts, rollback procedures

## Reporting Vulnerabilities

Please report security vulnerabilities to: security@snabagent.ru

We will respond within 48 hours and provide updates on remediation.
