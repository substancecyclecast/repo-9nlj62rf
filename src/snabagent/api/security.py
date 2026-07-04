"""Безопасность: пароли (bcrypt), JWT access tokens (15 min), refresh tokens (7 дней).

Используется для multi-tenant логина пользователей.
API-Key (Х-API-Key) остаётся отдельно — для machine-to-machine.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from ..settings import settings

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_MIN = 15
REFRESH_TOKEN_EXPIRES_DAYS = 7
_BCRYPT_ROUNDS = 12
_MAX_PW_BYTES = 72  # bcrypt limit


def _to_bytes(plain: str) -> bytes:
    b = plain.encode("utf-8")
    if len(b) > _MAX_PW_BYTES:
        b = b[:_MAX_PW_BYTES]
    return b


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(_to_bytes(plain), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_to_bytes(plain), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(claims: dict[str, Any], expires_min: int | None = None) -> str:
    to_encode = {**claims, "type": "access"}
    expire = datetime.now(UTC) + timedelta(minutes=expires_min or ACCESS_TOKEN_EXPIRES_MIN)
    to_encode["exp"] = int(expire.timestamp())
    secret = settings.secret_key.get_secret_value()
    return jwt.encode(to_encode, secret, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    to_encode = {
        "sub": user_id,
        "type": "refresh",
    }
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
    to_encode["exp"] = int(expire.timestamp())
    secret = settings.secret_key.get_secret_value()
    return jwt.encode(to_encode, secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    secret = settings.secret_key.get_secret_value()
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    """Verify a refresh token and return its claims, or None if invalid."""
    claims = decode_token(token)
    if claims is None:
        return None
    if claims.get("type") != "refresh":
        return None
    return claims
