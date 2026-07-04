"""WebSocket-роуты для live-обновлений лота. Канонический путь /ws/lots/{lot_id}."""
from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...settings import settings
from ..ws import bus

router = APIRouter(tags=["ws"])


@router.websocket("/ws/lots/{lot_id}")
async def ws_lot(websocket: WebSocket, lot_id: UUID, token: str | None = None) -> None:
    expected = settings.api_key.get_secret_value()
    # В dev-режиме с дефолтным dev-ключом пропускаем без токена.
    if not (settings.app_env == "dev" and expected.startswith("dev-")):
        if token != expected:
            await websocket.close(code=4401)
            return

    await websocket.accept()
    queue = await bus.subscribe(str(lot_id))
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_json(msg)
            except TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        await bus.unsubscribe(str(lot_id), queue)
