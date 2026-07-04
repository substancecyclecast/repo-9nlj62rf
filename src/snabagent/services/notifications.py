"""Notification channels: Telegram, Slack, generic Webhook."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..settings import settings

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Abstract notification channel."""

    @abstractmethod
    async def send(self, event: str, payload: dict[str, Any]) -> bool:
        """Send a notification. Returns True on success."""
        ...


class TelegramChannel(NotificationChannel):
    """Send notifications via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def send(self, event: str, payload: dict[str, Any]) -> bool:
        text = f"*SnabAgent — {event}*\n"
        for key, value in payload.items():
            text += f"  {key}: {value}\n"

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "Markdown",
                    },
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.warning("Telegram notification failed: %s", e)
            return False


class SlackChannel(NotificationChannel):
    """Send notifications via Slack incoming webhook."""

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def send(self, event: str, payload: dict[str, Any]) -> bool:
        text = f"*SnabAgent — {event}*\n"
        for key, value in payload.items():
            text += f"  {key}: {value}\n"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self.webhook_url,
                    json={"text": text},
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.warning("Slack notification failed: %s", e)
            return False


class WebhookChannel(NotificationChannel):
    """Send notifications via generic webhook POST."""

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {}

    async def send(self, event: str, payload: dict[str, Any]) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self.url,
                    json={"event": event, **payload},
                    headers=self.headers,
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.warning("Webhook notification failed: %s", e)
            return False


# Supported notification events
NOTIFICATION_EVENTS = [
    "lot_ready_for_review",
    "lot_escalated",
    "lot_approved",
    "daily_digest",
]


async def notify(event: str, payload: dict[str, Any], channels: list[NotificationChannel] | None = None) -> None:
    """Send notification to all configured channels."""
    if channels is None:
        channels = _default_channels()

    for ch in channels:
        try:
            await ch.send(event, payload)
        except Exception as e:
            logger.error("Notification channel %s failed: %s", type(ch).__name__, e)


def _default_channels() -> list[NotificationChannel]:
    """Build default channels from settings."""
    channels: list[NotificationChannel] = []
    bot_token = settings.telegram_bot_token.get_secret_value()
    chat_id = settings.telegram_escalation_chat_id
    if bot_token and chat_id:
        channels.append(TelegramChannel(bot_token, chat_id))
    return channels
