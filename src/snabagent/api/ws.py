"""Простой in-memory pub-sub для WebSocket /ws/lots/{lot_id}."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

log = logging.getLogger(__name__)


class LotEventBus:
    def __init__(self):
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, lot_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subs[lot_id].add(q)
        return q

    async def unsubscribe(self, lot_id: str, q: asyncio.Queue) -> None:
        async with self._lock:
            self._subs[lot_id].discard(q)
            if not self._subs[lot_id]:
                del self._subs[lot_id]

    async def publish(self, lot_id: str, message: dict[str, Any]) -> None:
        async with self._lock:
            subs = list(self._subs.get(lot_id, []))
        for q in subs:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:  # pragma: no cover
                log.warning("WS queue overflow for lot %s", lot_id)


bus = LotEventBus()
