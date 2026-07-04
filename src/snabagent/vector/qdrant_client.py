"""Qdrant-клиент. При недоступности Qdrant выдаёт InMemoryStore (для оффлайн-демо)."""
from __future__ import annotations

import logging
from typing import Any

from ..settings import settings
from .embeddings import cosine

_log = logging.getLogger(__name__)


class InMemoryVectorStore:
    """Простой in-memory store: поиск через cosine. Для оффлайн-демо."""

    def __init__(self):
        self._collections: dict[str, list[dict[str, Any]]] = {}

    def ensure(self, name: str) -> None:
        self._collections.setdefault(name, [])

    def upsert(self, name: str, points: list[dict]) -> None:
        self.ensure(name)
        # точки с одинаковым id заменяются
        existing = {p["id"]: i for i, p in enumerate(self._collections[name])}
        for p in points:
            if p["id"] in existing:
                self._collections[name][existing[p["id"]]] = p
            else:
                self._collections[name].append(p)

    def search(self, name: str, vector: list[float], limit: int = 5, payload_filter: dict | None = None):
        self.ensure(name)
        rows = self._collections[name]
        if payload_filter:
            rows = [r for r in rows if all(r["payload"].get(k) == v for k, v in payload_filter.items())]
        scored = []
        for r in rows:
            scored.append({"id": r["id"], "payload": r["payload"], "score": cosine(vector, r["vector"])})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def count(self, name: str) -> int:
        return len(self._collections.get(name, []))


_inmem = InMemoryVectorStore()


def in_memory_store() -> InMemoryVectorStore:
    return _inmem


async def get_async_qdrant():
    """Возвращает AsyncQdrantClient или None, если соединение недоступно."""
    try:
        from qdrant_client import AsyncQdrantClient
    except ImportError:
        return None
    api_key = settings.qdrant_api_key.get_secret_value() or None
    try:
        client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=api_key,
            timeout=2.0,
        )
        # проверка живости
        await client.get_collections()
        return client
    except Exception as e:  # pragma: no cover - тестируется только в integration
        _log.warning("Qdrant unavailable (%s), fallback to in-memory store", e)
        return None


async def ensure_collections() -> None:
    """Создаёт коллекции в Qdrant; если нет соединения — инициализирует in-memory."""
    client = await get_async_qdrant()
    if client is None:
        _inmem.ensure(settings.qdrant_nsi_collection)
        _inmem.ensure(settings.qdrant_suppliers_collection)
        return

    from qdrant_client.models import Distance, VectorParams

    existing = {c.name for c in (await client.get_collections()).collections}
    for name in (settings.qdrant_nsi_collection, settings.qdrant_suppliers_collection):
        if name in existing:
            continue
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
        )


async def upsert_points(collection: str, points: list[dict]) -> None:
    client = await get_async_qdrant()
    if client is None:
        _inmem.upsert(collection, points)
        return
    from qdrant_client.models import PointStruct

    qpoints = [PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points]
    await client.upsert(collection_name=collection, points=qpoints)


async def search(collection: str, vector: list[float], limit: int = 5, payload_filter: dict | None = None):
    client = await get_async_qdrant()
    if client is None:
        return _inmem.search(collection, vector, limit=limit, payload_filter=payload_filter)
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    qfilter = None
    if payload_filter:
        qfilter = Filter(
            must=[FieldCondition(key=k, match=MatchValue(value=v)) for k, v in payload_filter.items()]
        )
    res = await client.search(
        collection_name=collection,
        query_vector=vector,
        limit=limit,
        query_filter=qfilter,
        with_payload=True,
    )
    return [{"id": str(p.id), "payload": p.payload or {}, "score": p.score} for p in res]
