"""Поиск исторических поставщиков по SKU. Используется Sourcer-агентом."""
from __future__ import annotations

from sqlalchemy import select

from ...db.models import HistoricalPurchase, Supplier
from ...db.session import AsyncSessionLocal


async def lookup_by_skus(customer_id: str, skus: list[str]) -> list[dict]:
    if not skus:
        return []
    async with AsyncSessionLocal() as s:
        q = (
            select(Supplier, HistoricalPurchase)
            .join(HistoricalPurchase, HistoricalPurchase.supplier_id == Supplier.id)
            .where(HistoricalPurchase.customer_id == str(customer_id))
            .where(HistoricalPurchase.nsi_sku.in_(skus))
        )
        rows = (await s.execute(q)).all()
    seen: dict[str, dict] = {}
    for supplier, hist in rows:
        if supplier.inn in seen:
            seen[supplier.inn]["hist_count"] += 1
            continue
        seen[supplier.inn] = {
            "supplier_id": str(supplier.id),
            "inn": supplier.inn,
            "ogrn": supplier.ogrn,
            "name": supplier.name,
            "contact_email": supplier.contact_email,
            "website": supplier.website,
            "region": supplier.region,
            "categories": supplier.categories or [],
            "historical_score": supplier.historical_score,
            "avg_response_time_hours": supplier.avg_response_time_hours,
            "source": "historical",
            "hist_count": 1,
            "reasoning": (
                f"Поставлял этот SKU; on-time={hist.on_time}; quality={hist.quality_score}"
            ),
        }
    return list(seen.values())
