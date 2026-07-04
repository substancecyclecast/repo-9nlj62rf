"""Telegram bot polling runner for SnabAgent.

Runs in long-polling mode (no HTTPS required).
Usage: python -m snabagent.bot.polling_runner
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("snabagent.bot.polling")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API_BASE = os.environ.get("SNABAGENT_API_BASE", "http://localhost:8000")
API_KEY = os.environ.get("SNABAGENT_API_KEY", "dev-only-key-change-in-prod")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(chat_id: str, text: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            )
    except Exception as e:
        logger.error("Failed to send message: %s", e)


async def process_update(update: dict) -> None:
    message = update.get("message", {})
    text = message.get("text", "")
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not chat_id or not text:
        return

    from .telegram_bot import (
        handle_approve,
        handle_escalate,
        handle_help,
        handle_lot_detail,
        handle_new_lot,
        handle_start,
        handle_status,
    )

    if text.startswith("/start"):
        reply = await handle_start(chat_id)
    elif text.startswith("/new "):
        reply = await handle_new_lot(chat_id, text[5:])
    elif text == "/new":
        reply = "Укажите описание заявки: /new <описание>"
    elif text.startswith("/status"):
        reply = await handle_status(chat_id)
    elif text.startswith("/lot "):
        reply = await handle_lot_detail(chat_id, text[5:].strip())
    elif text.startswith("/approve "):
        reply = await handle_approve(chat_id, text[9:].strip())
    elif text.startswith("/escalate "):
        reply = await handle_escalate(chat_id, text[10:].strip())
    elif text.startswith("/help"):
        reply = await handle_help(chat_id)
    else:
        reply = await handle_help(chat_id)

    await send_message(chat_id, reply)


async def delete_webhook() -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{TELEGRAM_API}/deleteWebhook")
        logger.info("deleteWebhook: %s", resp.json())


async def poll_updates() -> None:
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    # Delete any existing webhook to enable polling
    await delete_webhook()

    # Get bot info
    async with httpx.AsyncClient(timeout=10) as client:
        me = await client.get(f"{TELEGRAM_API}/getMe")
        bot_info = me.json().get("result", {})
        logger.info(
            "Bot started: @%s (%s)",
            bot_info.get("username", "unknown"),
            bot_info.get("first_name", "unknown"),
        )

    offset = 0
    logger.info("Polling for updates...")

    while True:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                resp = await client.get(
                    f"{TELEGRAM_API}/getUpdates",
                    params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                )
                data = resp.json()

                if not data.get("ok"):
                    logger.error("getUpdates error: %s", data)
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    try:
                        await process_update(update)
                    except Exception as e:
                        logger.error("Error processing update: %s", e)

        except httpx.TimeoutException:
            continue
        except Exception as e:
            logger.error("Polling error: %s", e)
            await asyncio.sleep(5)


def main() -> None:
    asyncio.run(poll_updates())


if __name__ == "__main__":
    main()
