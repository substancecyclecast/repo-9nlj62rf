"""Авторизация: X-API-Key (machine-to-machine) + JWT (per-user).

Дизайн:
- M2M вызовы (CI, n8n) шлют X-API-Key или Authorization: Bearer <api_key>.
  Они получают "system principal": role=admin, customer_id=None → видят всё.
- User-вызовы из Streamlit шлют JWT-токен в Authorization: Bearer.
  Токен содержит {sub: user_id, customer_id, role, email}.

Backward compat:
- В dev-режиме (app_env=dev И api_key начинается с "dev-") пропускаем все запросы
  без проверки → возвращаем "system principal".
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, Request, status

from ..settings import settings
from .security import decode_token


@dataclass(frozen=True)
class Principal:
    """Кого видит каждый эндпоинт. Универсальный объект."""

    kind: str  # "system" | "user"
    user_id: UUID | None
    customer_id: UUID | None
    role: str  # "admin" | "buyer" | "viewer"
    email: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_system(self) -> bool:
        return self.kind == "system"

    def filter_customer_id(self) -> UUID | None:
        """Какой customer_id подставлять в WHERE.

        Admin/system видят всё → None. Обычный user — только свой customer.
        """
        if self.is_system or self.is_admin:
            return None
        return self.customer_id


SYSTEM_PRINCIPAL = Principal(
    kind="system", user_id=None, customer_id=None, role="admin", email=None
)


# Пути, не требующие авторизации
_OPEN_PATHS = (
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/metrics",
    "/auth/login",
    "/auth/register",
    "/auth/verify-email",
    "/webhooks/telegram",
)


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def _principal_from_jwt(token: str) -> Principal | None:
    payload = decode_token(token)
    if not payload:
        return None
    try:
        return Principal(
            kind="user",
            user_id=UUID(payload["sub"]),
            customer_id=UUID(payload["customer_id"]) if payload.get("customer_id") else None,
            role=payload.get("role", "viewer"),
            email=payload.get("email"),
        )
    except (KeyError, ValueError, TypeError):
        return None


def _is_dev_bypass() -> bool:
    expected = settings.api_key.get_secret_value()
    return settings.app_env == "dev" and expected.startswith("dev-")


async def require_principal(request: Request) -> Principal:
    """FastAPI-зависимость: возвращает Principal или 401."""
    path = request.url.path

    # WebSocket-проверка делается внутри роута через query-param token
    if path.startswith("/ws/"):
        return SYSTEM_PRINCIPAL

    if any(path == p or path.startswith(p + "/") or path.startswith(p) for p in _OPEN_PATHS):
        return SYSTEM_PRINCIPAL

    expected = settings.api_key.get_secret_value()

    # 1) Берём из заголовков
    x_api_key = request.headers.get("x-api-key")
    bearer = _extract_bearer(request)

    # 2) JWT имеет приоритет — если задан Bearer и это валидный JWT, используем его
    if bearer and bearer != expected:
        principal = _principal_from_jwt(bearer)
        if principal:
            request.state.principal = principal
            return principal

    # 3) X-API-Key или Bearer == api_key → system
    if x_api_key and x_api_key == expected:
        request.state.principal = SYSTEM_PRINCIPAL
        return SYSTEM_PRINCIPAL
    if bearer and bearer == expected:
        request.state.principal = SYSTEM_PRINCIPAL
        return SYSTEM_PRINCIPAL

    # 4) Dev-bypass без credentials — для локального запуска оффлайн-демо
    if _is_dev_bypass() and not (bearer or x_api_key):
        request.state.principal = SYSTEM_PRINCIPAL
        return SYSTEM_PRINCIPAL

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Backward-compat: старое имя
require_api_key = require_principal


def get_principal(request: Request) -> Principal:
    """Извлекает Principal, проставленный require_principal. Для использования
    внутри обработчика."""
    return getattr(request.state, "principal", SYSTEM_PRINCIPAL)
