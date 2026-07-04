"""Индексация поставщиков в Qdrant."""
from __future__ import annotations

from sqlalchemy import select

from ..db.models import Supplier
from ..db.session import AsyncSessionLocal
from ..settings import settings
from . import qdrant_client
from .embeddings import embed_passages


def _supplier_text(s: Supplier) -> str:
    return (
        f"{s.name} (категории {','.join(s.categories or [])}, "
        f"регион {s.region or '—'}, ОКВЭД {','.join(s.okved_codes or [])})"
    )


async def reindex_suppliers() -> int:
    await qdrant_client.ensure_collections()
    async with AsyncSessionLocal() as session:
        rows = list((await session.execute(select(Supplier))).scalars().all())
    if not rows:
        return 0
    vectors = embed_passages([_supplier_text(s) for s in rows])
    points = [
        {
            "id": str(s.id),
            "vector": v,
            "payload": {
                "supplier_id": str(s.id),
                "inn": s.inn,
                "ogrn": s.ogrn,
                "name": s.name,
                "categories": s.categories or [],
                "region": s.region,
                "contact_email": s.contact_email,
                "website": s.website,
                "historical_score": s.historical_score,
                "source": s.source,
            },
        }
        for s, v in zip(rows, vectors, strict=False)
    ]
    await qdrant_client.upsert_points(settings.qdrant_suppliers_collection, points)
    return len(points)
