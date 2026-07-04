"""Tests for security module: JWT, password hashing."""
from __future__ import annotations

from snabagent.api.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)


def test_hash_and_verify_password():
    pw = "TestP@ss1!"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed) is True


def test_wrong_password():
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_access_token():
    payload = {"sub": "user-1", "role": "admin", "email": "a@b.com"}
    token = create_access_token(payload)
    assert isinstance(token, str)
    assert len(token) > 20


def test_create_and_verify_refresh_token():
    token = create_refresh_token("user-1")
    claims = verify_refresh_token(token)
    assert claims is not None
    assert claims["sub"] == "user-1"


def test_verify_invalid_refresh_token():
    result = verify_refresh_token("invalid-token")
    assert result is None
