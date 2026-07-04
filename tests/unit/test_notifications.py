"""Tests for notification channels."""
from __future__ import annotations

import pytest

from snabagent.services.notifications import (
    NOTIFICATION_EVENTS,
    SlackChannel,
    TelegramChannel,
    WebhookChannel,
)


def test_notification_events():
    assert "lot_ready_for_review" in NOTIFICATION_EVENTS
    assert "lot_escalated" in NOTIFICATION_EVENTS
    assert "lot_approved" in NOTIFICATION_EVENTS
    assert "daily_digest" in NOTIFICATION_EVENTS


def test_telegram_channel_init():
    ch = TelegramChannel(bot_token="test-token", chat_id="12345")
    assert ch.bot_token == "test-token"
    assert ch.chat_id == "12345"


def test_slack_channel_init():
    ch = SlackChannel(webhook_url="https://hooks.slack.com/test")
    assert ch.webhook_url == "https://hooks.slack.com/test"


def test_webhook_channel_init():
    ch = WebhookChannel(url="https://example.com/hook", headers={"X-Key": "val"})
    assert ch.url == "https://example.com/hook"
    assert ch.headers["X-Key"] == "val"


def test_webhook_channel_default_headers():
    ch = WebhookChannel(url="https://example.com/hook")
    assert ch.headers == {}


@pytest.mark.asyncio
async def test_telegram_send_no_token():
    ch = TelegramChannel(bot_token="fake-token", chat_id="123")
    result = await ch.send("test_event", {"key": "value"})
    assert result is False


@pytest.mark.asyncio
async def test_slack_send_invalid_url():
    ch = SlackChannel(webhook_url="http://invalid.local/hook")
    result = await ch.send("test_event", {"key": "value"})
    assert result is False
