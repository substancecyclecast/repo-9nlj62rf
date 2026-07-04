"""Extended telegram bot tests with mocked API calls."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snabagent.bot.telegram_bot import (
    handle_lot_detail,
    handle_new_lot,
    handle_status,
)


@pytest.fixture
def event_loop_for_test():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


def test_handle_new_lot_empty_desc(event_loop_for_test):
    result = event_loop_for_test.run_until_complete(handle_new_lot("1", ""))
    assert "описание" in result.lower() or "/new" in result


def test_handle_lot_detail_empty_id(event_loop_for_test):
    result = event_loop_for_test.run_until_complete(handle_lot_detail("1", ""))
    assert "ID" in result or "/lot" in result


def test_handle_new_lot_success_mock(event_loop_for_test):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "abc-123", "status": "draft"}

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("snabagent.bot.telegram_bot.httpx.AsyncClient", return_value=mock_client):
        result = event_loop_for_test.run_until_complete(
            handle_new_lot("1", "Нужны болты М10")
        )
    assert "abc-123" in result or "Лот создан" in result


def test_handle_status_success_mock(event_loop_for_test):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"id": "lot-1", "status": "draft", "category": "Трубы"},
        {"id": "lot-2", "status": "approved", "category": "Арматура"},
    ]

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("snabagent.bot.telegram_bot.httpx.AsyncClient", return_value=mock_client):
        result = event_loop_for_test.run_until_complete(handle_status("1"))
    assert "lot-1" in result or "лот" in result.lower()


def test_handle_lot_detail_success_mock(event_loop_for_test):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "lot-detail-1",
        "status": "report_ready",
        "category": "Трубы",
        "phase": "pre_nmck",
        "final_report": {"savings_pct": 12.5, "top_3": [
            {"supplier": "S1", "total_price": 100000, "delivery_days": 5},
        ]},
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("snabagent.bot.telegram_bot.httpx.AsyncClient", return_value=mock_client):
        result = event_loop_for_test.run_until_complete(
            handle_lot_detail("1", "lot-detail-1")
        )
    assert "lot-detail" in result or "Статус" in result


def test_handle_status_empty_list_mock(event_loop_for_test):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = []

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("snabagent.bot.telegram_bot.httpx.AsyncClient", return_value=mock_client):
        result = event_loop_for_test.run_until_complete(handle_status("1"))
    assert "Нет активных" in result or "нет" in result.lower()


def test_handle_new_lot_api_error_mock(event_loop_for_test):
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("snabagent.bot.telegram_bot.httpx.AsyncClient", return_value=mock_client):
        result = event_loop_for_test.run_until_complete(
            handle_new_lot("1", "Болты")
        )
    assert "Ошибка" in result or "500" in result
