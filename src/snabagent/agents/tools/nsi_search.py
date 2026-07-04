"""Семантический поиск НСИ-кандидатов через векторное хранилище."""
from __future__ import annotations

from ...settings import settings
from ...vector import qdrant_client
from ...vector.embeddings import embed_queries


async def nsi_search(query: str, customer_id: str | None = None, top_k: int = 5) -> list[dict]:
    vec = embed_queries([query])[0]
    results: list[dict] = []
    if customer_id:
        results = await qdrant_client.search(
            settings.qdrant_nsi_collection,
            vec,
            limit=top_k,
            payload_filter={"customer_id": str(customer_id)},
        )
    # Фолбэк на общий справочник НСИ, если у тенанта нет своих позиций
    # (multi-tenant MVP использует общий каталог-эталон).
    if not results:
        results = await qdrant_client.search(
            settings.qdrant_nsi_collection,
            vec,
            limit=top_k,
            payload_filter=None,
        )
    out = []
    for r in results:
        p = r["payload"]
        out.append(
            {
                "nsi_id": p.get("nsi_id"),
                "sku": p.get("sku"),
                "name": p.get("name"),
                "full_name": p.get("full_name"),
                "category": p.get("category"),
                "unit": p.get("unit") or "",
                "gost": p.get("gost") or "",
                "typical_price_rub": p.get("typical_price_rub"),
                "score": float(r.get("score") or 0.0),
            }
        )
    return out
