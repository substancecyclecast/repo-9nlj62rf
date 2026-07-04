"""Репозитории с типизированным API. Используется как FastAPI dependency."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AuditLog,
    Customer,
    HistoricalPurchase,
    Lot,
    LotStatus,
    Negotiation,
    NsiItem,
    RfqEmail,
    Supplier,
    User,
    UserRole,
    Verification,
)


class LotRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: dict) -> Lot:
        lot = Lot(**payload)
        self.session.add(lot)
        await self.session.commit()
        await self.session.refresh(lot)
        return lot

    async def get(self, lot_id: UUID | str) -> Lot | None:
        return await self.session.get(Lot, str(lot_id))

    async def list(
        self,
        *,
        limit: int = 50,
        customer_id: UUID | str | None = None,
        status: LotStatus | None = None,
        offset: int = 0,
    ) -> list[Lot]:
        q = select(Lot).order_by(Lot.created_at.desc()).limit(limit).offset(offset)
        if customer_id is not None:
            q = q.where(Lot.customer_id == str(customer_id))
        if status is not None:
            q = q.where(Lot.status == status)
        return list((await self.session.execute(q)).scalars().all())

    async def count(
        self,
        *,
        customer_id: UUID | str | None = None,
        status: LotStatus | None = None,
    ) -> int:
        q = select(func.count()).select_from(Lot)
        if customer_id is not None:
            q = q.where(Lot.customer_id == str(customer_id))
        if status is not None:
            q = q.where(Lot.status == status)
        result = await self.session.execute(q)
        return result.scalar() or 0

    async def update_status(self, lot_id: UUID | str, status: LotStatus, **fields: Any) -> None:
        stmt = (
            update(Lot)
            .where(Lot.id == str(lot_id))
            .values(status=status, updated_at=datetime.now(UTC), **fields)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def set_report(self, lot_id: UUID | str, report: dict) -> None:
        await self.update_status(lot_id, LotStatus.report_ready, final_report=report)

    async def approve(self, lot_id: UUID | str, supplier_id: UUID | str, reviewer: str | None) -> Lot:
        await self.update_status(
            lot_id,
            LotStatus.approved,
            chosen_supplier_id=str(supplier_id) if supplier_id else None,
            closed_at=datetime.now(UTC),
        )
        lot = await self.get(lot_id)
        assert lot is not None
        return lot

    async def audit_log(self, lot_id: UUID | str) -> list[AuditLog]:
        q = (
            select(AuditLog)
            .where(AuditLog.lot_id == str(lot_id))
            .order_by(AuditLog.created_at)
        )
        return list((await self.session.execute(q)).scalars().all())

    async def rfq_emails(self, lot_id: UUID | str) -> list[RfqEmail]:
        q = select(RfqEmail).where(RfqEmail.lot_id == str(lot_id))
        return list((await self.session.execute(q)).scalars().all())


class CustomerRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, name: str, inn: str | None = None) -> Customer:
        q = select(Customer).where(Customer.name == name)
        existing = (await self.session.execute(q)).scalars().first()
        if existing:
            return existing
        c = Customer(name=name, inn=inn)
        self.session.add(c)
        await self.session.commit()
        await self.session.refresh(c)
        return c


class NsiRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_customer(self, customer_id: UUID | str) -> list[NsiItem]:
        q = select(NsiItem).where(NsiItem.customer_id == str(customer_id))
        return list((await self.session.execute(q)).scalars().all())

    async def by_sku(self, customer_id: UUID | str, sku: str) -> NsiItem | None:
        q = select(NsiItem).where(NsiItem.customer_id == str(customer_id), NsiItem.sku == sku)
        return (await self.session.execute(q)).scalars().first()


class SupplierRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_inn(self, inn: str) -> Supplier | None:
        q = select(Supplier).where(Supplier.inn == inn)
        return (await self.session.execute(q)).scalars().first()

    async def by_category(self, category: str, limit: int = 50) -> list[Supplier]:
        # SQLite не поддерживает JSON-операторы, поэтому делаем простую LIKE-фильтрацию
        q = select(Supplier).limit(limit)
        rows = list((await self.session.execute(q)).scalars().all())
        return [s for s in rows if (s.categories or []) and category in s.categories]

    async def historical_for_sku(self, sku: str) -> list[Supplier]:
        q = (
            select(Supplier)
            .join(HistoricalPurchase, HistoricalPurchase.supplier_id == Supplier.id)
            .where(HistoricalPurchase.nsi_sku == sku)
        )
        return list((await self.session.execute(q)).scalars().unique().all())


class NegotiationRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs: Any) -> Negotiation:
        n = Negotiation(**kwargs)
        self.session.add(n)
        await self.session.commit()
        await self.session.refresh(n)
        return n


class VerificationRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs: Any) -> Verification:
        v = Verification(**kwargs)
        self.session.add(v)
        await self.session.commit()
        await self.session.refresh(v)
        return v


class RfqEmailRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs: Any) -> RfqEmail:
        m = RfqEmail(**kwargs)
        self.session.add(m)
        await self.session.commit()
        await self.session.refresh(m)
        return m


class UserRepo:
    """CRUD пользователей + поиск по email."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def by_email(self, email: str) -> User | None:
        q = select(User).where(User.email == email.lower())
        return (await self.session.execute(q)).scalars().first()

    async def get(self, user_id: UUID | str) -> User | None:
        return await self.session.get(User, str(user_id))

    async def create(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str | None = None,
        customer_id: UUID | str | None = None,
        role: UserRole = UserRole.buyer,
        approval_limit_rub: float | None = None,
    ) -> User:
        u = User(
            email=email.lower(),
            hashed_password=hashed_password,
            full_name=full_name,
            customer_id=str(customer_id) if customer_id else None,
            role=role,
            approval_limit_rub=approval_limit_rub,
        )
        self.session.add(u)
        await self.session.commit()
        await self.session.refresh(u)
        return u

    async def touch_last_login(self, user_id: UUID | str) -> None:
        stmt = (
            update(User)
            .where(User.id == str(user_id))
            .values(last_login_at=datetime.now(UTC))
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def by_verify_token(self, token: str) -> User | None:
        q = select(User).where(User.email_verify_token == token)
        return (await self.session.execute(q)).scalars().first()

    async def list(self, *, customer_id: UUID | str | None = None, limit: int = 100) -> list[User]:
        q = select(User).order_by(User.created_at.desc()).limit(limit)
        if customer_id is not None:
            q = q.where(User.customer_id == str(customer_id))
        return list((await self.session.execute(q)).scalars().all())
