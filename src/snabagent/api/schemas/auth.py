"""Pydantic-схемы для auth-роутов."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class UserRoleEnum(str, Enum):
    admin = "admin"
    buyer = "buyer"
    viewer = "viewer"


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 15 * 60
    user_id: UUID
    customer_id: UUID | None
    role: UserRoleEnum
    email: str


class RefreshIn(BaseModel):
    refresh_token: str


class RefreshOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 15 * 60


class UserOut(BaseModel):
    id: UUID
    customer_id: UUID | None
    email: str
    full_name: str | None
    role: UserRoleEnum
    approval_limit_rub: float | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class UserCreateIn(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    customer_id: UUID | None = None
    role: UserRoleEnum = UserRoleEnum.buyer
    approval_limit_rub: float | None = None


class RegisterIn(BaseModel):
    email: str
    password: str
    full_name: str
    company_name: str
    inn: str | None = None
    phone: str | None = None


class RegisterOut(BaseModel):
    user_id: UUID
    customer_id: UUID
    email: str
    message: str
