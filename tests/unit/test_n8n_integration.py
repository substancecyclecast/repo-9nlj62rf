"""Unit-тесты для n8n-эскалации."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from snabagent.integrations.n8n import notify_alert, notify_escalation


@pytest.mark.asyncio
async def test_escalation_skipped_without_url():
    with patch("snabagent.integrations.n8n.settings") as mock_settings:
        mock_settings.n8n_webhook_escalation = None
        mock_settings.service_public_url = "http://x"
        ok = await notify_escalation(
            lot_id="abc",
            severity="high",
            reason="no candidates",
        )
        assert ok is False


@pytest.mark.asyncio
async def test_escalation_does_not_raise_on_http_error():
    import httpx

    with patch("snabagent.integrations.n8n.settings") as mock_settings:
        mock_settings.n8n_webhook_escalation = "http://invalid/n8n"
        mock_settings.service_public_url = "http://x"
        # Mock AsyncClient → raises HTTPError
        with patch("snabagent.integrations.n8n.httpx.AsyncClient") as ctor:
            client_instance = AsyncMock()
            client_instance.__aenter__.return_value = client_instance
            client_instance.post.side_effect = httpx.ConnectError("boom")
            ctor.return_value = client_instance
            ok = await notify_escalation(lot_id="lid", severity="high", reason="r")
            assert ok is False


@pytest.mark.asyncio
async def test_alert_returns_false_without_url():
    with patch("snabagent.integrations.n8n.settings") as mock_settings:
        mock_settings.n8n_webhook_escalation = None
        ok = await notify_alert(title="t", message="m")
        assert ok is False
