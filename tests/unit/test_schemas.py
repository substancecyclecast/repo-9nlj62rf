"""Tests for pydantic schemas."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from snabagent.api.schemas.auth import LoginIn, RegisterIn, UserRoleEnum
from snabagent.api.schemas.lot import LotCreateIn, PaginatedLots


def test_login_in_valid():
    m = LoginIn(email="a@b.com", password="pass")
    assert m.email == "a@b.com"


def test_login_in_missing_email():
    with pytest.raises(ValidationError):
        LoginIn(password="pass")


def test_register_in_valid():
    m = RegisterIn(
        email="a@b.com",
        password="P@ss1234!",
        full_name="Test",
        company_name="Co",
    )
    assert m.email == "a@b.com"
    assert m.inn is None
    assert m.phone is None


def test_register_in_with_optional():
    m = RegisterIn(
        email="a@b.com",
        password="P@ss1234!",
        full_name="Test",
        company_name="Co",
        inn="1234567890",
        phone="+79001234567",
    )
    assert m.inn == "1234567890"


def test_user_role_enum():
    assert UserRoleEnum.admin.value == "admin"
    assert UserRoleEnum.buyer.value == "buyer"


def test_lot_create_in():
    m = LotCreateIn(
        customer_name="Test",
        raw_request="Нужны болты",
        phase="pre_nmck",
    )
    assert m.customer_name == "Test"


def test_paginated_lots():
    m = PaginatedLots(items=[], total=0, page=1, page_size=20, pages=0)
    assert m.total == 0
    assert len(m.items) == 0
