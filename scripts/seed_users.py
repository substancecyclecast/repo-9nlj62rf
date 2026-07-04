"""Создаёт демо-пользователей: admin, buyer, viewer.

Пароли в .env / переменных окружения:
  DEMO_ADMIN_PASSWORD (default: admin123)
  DEMO_BUYER_PASSWORD (default: buyer123)
  DEMO_VIEWER_PASSWORD (default: viewer123)
"""
from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from sqlalchemy import select

from snabagent.api.security import hash_password
from snabagent.db.models import Base, Customer, User, UserRole
from snabagent.db.session import AsyncSessionLocal, engine

DEFAULT_USERS = [
    {
        "email": "admin@sibur.demo",
        "password_env": "DEMO_ADMIN_PASSWORD",
        "password_default": "admin123",
        "role": UserRole.admin,
        "full_name": "Demo Admin",
        "approval_limit_rub": None,
    },
    {
        "email": "buyer@sibur.demo",
        "password_env": "DEMO_BUYER_PASSWORD",
        "password_default": "buyer123",
        "role": UserRole.buyer,
        "full_name": "Demo Buyer",
        "approval_limit_rub": 5_000_000.0,
    },
    {
        "email": "viewer@sibur.demo",
        "password_env": "DEMO_VIEWER_PASSWORD",
        "password_default": "viewer123",
        "role": UserRole.viewer,
        "full_name": "Demo Viewer",
        "approval_limit_rub": None,
    },
]


async def _ensure_customer(session, name: str, inn: str | None = None) -> Customer:
    existing = (await session.execute(select(Customer).where(Customer.name == name))).scalars().first()
    if existing:
        return existing
    c = Customer(id=uuid4(), name=name, inn=inn)
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return c


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        sibur = await _ensure_customer(session, "SIBUR Demo", "7728168971")
        await _ensure_customer(session, "Severstal Demo", "7825706086")
        await _ensure_customer(session, "Government Demo")

        for u in DEFAULT_USERS:
            email = u["email"].lower()
            existing = (await session.execute(select(User).where(User.email == email))).scalars().first()
            if existing:
                continue
            session.add(
                User(
                    customer_id=sibur.id,
                    email=email,
                    hashed_password=hash_password(os.environ.get(u["password_env"], u["password_default"])),
                    full_name=u["full_name"],
                    role=u["role"],
                    approval_limit_rub=u["approval_limit_rub"],
                )
            )
        await session.commit()
        print("Seeded users:")
        for u in DEFAULT_USERS:
            print(f"  {u['email']}  ({u['role'].value})  pw={os.environ.get(u['password_env'], u['password_default'])}")


if __name__ == "__main__":
    asyncio.run(main())
