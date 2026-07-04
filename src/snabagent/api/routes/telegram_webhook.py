"""Telegram webhook endpoint — receives updates from Telegram Bot API."""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request

from ...settings import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

logger = logging.getLogger(__name__)


async def _send_telegram_message(chat_id: str, text: str) -> None:
    """Send a message via Telegram Bot API."""
    bot_token = settings.telegram_bot_token.get_secret_value()
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping send")
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    except Exception as e:
        logger.error("Failed to send Telegram message: %s", e)


@router.post("/telegram")
async def telegram_webhook(request: Request):
    """Receive webhook updates from Telegram."""
    from ...bot.telegram_bot import (
        handle_approve,
        handle_escalate,
        handle_help,
        handle_lot_detail,
        handle_new_lot,
        handle_start,
        handle_status,
    )

    data = await request.json()
    message = data.get("message", {})
    text = message.get("text", "")
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not chat_id or not text:
        return {"ok": True}

    if text.startswith("/start"):
        reply = await handle_start(chat_id)
    elif text.startswith("/new "):
        reply = await handle_new_lot(chat_id, text[5:])
    elif text.startswith("/status"):
        reply = await handle_status(chat_id)
    elif text.startswith("/lot "):
        reply = await handle_lot_detail(chat_id, text[5:].strip())
    elif text.startswith("/approve "):
        reply = await handle_approve(chat_id, text[9:].strip())
    elif text.startswith("/escalate "):
        reply = await handle_escalate(chat_id, text[10:].strip())
    else:
        reply = await handle_help(chat_id)

    await _send_telegram_message(chat_id, reply)
    return {"ok": True}


@router.post("/telegram/set-webhook")
async def set_telegram_webhook(request: Request):
    """Register the webhook URL with Telegram Bot API."""
    bot_token = settings.telegram_bot_token.get_secret_value()
    if not bot_token:
        return {"error": "TELEGRAM_BOT_TOKEN not configured"}

    webhook_url = f"{settings.service_public_url}/api/v1/webhooks/telegram"
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json={"url": webhook_url})
        return resp.json()
