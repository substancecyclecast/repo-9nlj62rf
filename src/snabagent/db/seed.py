"""Загрузка mock-CSV в DB. Используется scripts/seed_db.py."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from .models import Base, Customer, HistoricalPurchase, NsiItem, Supplier
from .session import AsyncSessionLocal, engine

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"


async def seed_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as s:
        existing = (await s.execute(select(Customer).where(Customer.name == "SIBUR Demo"))).scalars().first()
        if existing:
            customer = existing
        else:
            customer = Customer(id=uuid4(), name="SIBUR Demo", inn="7728168971")
            s.add(customer)
            await s.commit()
            await s.refresh(customer)

        # NSI
        nsi_path = DATA / "nsi_sample.csv"
        if nsi_path.exists():
            with nsi_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            for r in rows:
                exists = (
                    await s.execute(
                        select(NsiItem).where(
                            NsiItem.customer_id == str(customer.id), NsiItem.sku == r["sku"]
                        )
                    )
                ).scalars().first()
                if exists:
                    continue
                s.add(
                    NsiItem(
                        customer_id=customer.id,
                        sku=r["sku"],
                        name=r["name"],
                        full_name=r["full_name"],
                        category=r["category"],
                        unit=r["unit"],
                        gost=r.get("gost") or None,
                        typical_price_rub=float(r["typical_price_rub"]) if r["typical_price_rub"] else None,
                        attributes=json.loads(r["attributes"]) if r.get("attributes") else {},
                    )
                )
            await s.commit()

        # Suppliers
        sup_path = DATA / "suppliers_seed.csv"
        if sup_path.exists():
            with sup_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            for r in rows:
                exists = (
                    await s.execute(select(Supplier).where(Supplier.inn == r["inn"]))
                ).scalars().first()
                if exists:
                    continue
                s.add(
                    Supplier(
                        inn=r["inn"],
                        ogrn=r.get("ogrn") or None,
                        name=r["name"],
                        short_name=r.get("short_name") or None,
                        legal_address=r.get("legal_address") or None,
                        contact_email=r.get("contact_email") or None,
                        contact_phone=r.get("contact_phone") or None,
                        website=r.get("website") or None,
                        okved_codes=(r.get("okved_codes") or "").split("|") if r.get("okved_codes") else [],
                        categories=[r.get("categories")] if r.get("categories") else [],
                        region=r.get("region") or None,
                        avg_response_time_hours=int(r["avg_response_time_hours"]) if r.get("avg_response_time_hours") else None,
                        historical_score=float(r["historical_score"]) if r.get("historical_score") else None,
                        source=r.get("source") or "seed",
                    )
                )
            await s.commit()

        # Historical purchases
        hist_path = DATA / "historical_purchases.csv"
        if hist_path.exists():
            with hist_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            inn_to_id = {
                sup.inn: sup.id
                for sup in (await s.execute(select(Supplier))).scalars().all()
            }
            for r in rows:
                supplier_id = inn_to_id.get(r["supplier_inn"])
                if not supplier_id:
                    continue
                s.add(
                    HistoricalPurchase(
                        customer_id=customer.id,
                        supplier_id=supplier_id,
                        nsi_sku=r["nsi_sku"],
                        qty=float(r["qty"]) if r.get("qty") else None,
                        unit=r.get("unit"),
                        price_rub=float(r["price_rub"]) if r.get("price_rub") else None,
                        purchase_date=r.get("purchase_date"),
                        on_time=r["on_time"].lower() == "true" if r.get("on_time") else None,
                        quality_score=float(r["quality_score"]) if r.get("quality_score") else None,
                    )
                )
            await s.commit()
