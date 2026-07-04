"""Индексация НСИ в векторное хранилище (Qdrant или InMemory)."""
from __future__ import annotations

from sqlalchemy import select

from ..db.models import NsiItem
from ..db.session import AsyncSessionLocal
from ..settings import settings
from . import qdrant_client
from .embeddings import embed_passages


async def reindex_nsi(customer_id: str | None = None) -> int:
    """Полная переиндексация НСИ. Возвращает количество загруженных точек."""
    await qdrant_client.ensure_collections()
    async with AsyncSessionLocal() as s:
        q = select(NsiItem)
        if customer_id:
            q = q.where(NsiItem.customer_id == str(customer_id))
        rows = list((await s.execute(q)).scalars().all())
    if not rows:
        return 0
    texts = [
        f"{r.full_name or r.name} (категория {r.category}; ед.изм. {r.unit or '—'}; ГОСТ {r.gost or '—'})"
        for r in rows
    ]
    vectors = embed_passages(texts)
    points = [
        {
            "id": str(r.id),
            "vector": v,
            "payload": {
                "nsi_id": str(r.id),
                "sku": r.sku,
                "name": r.name,
                "full_name": r.full_name,
                "category": r.category,
                "unit": r.unit,
                "gost": r.gost,
                "typical_price_rub": float(r.typical_price_rub) if r.typical_price_rub else None,
                "customer_id": str(r.customer_id),
                "attributes": r.attributes or {},
            },
        }
        for r, v in zip(rows, vectors, strict=False)
    ]
    await qdrant_client.upsert_points(settings.qdrant_nsi_collection, points)
    return len(points)
