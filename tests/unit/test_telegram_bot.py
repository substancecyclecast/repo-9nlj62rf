"""Tests for telegram bot command handlers."""
from __future__ import annotations

import asyncio

import pytest

from snabagent.bot.telegram_bot import (
    handle_help,
    handle_new_lot,
    handle_start,
    handle_status,
)


@pytest.fixture
def event_loop_for_test():
    """Create a new event loop for tests that need it."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


def test_handle_start(event_loop_for_test):
    result = event_loop_for_test.run_until_complete(handle_start("123"))
    assert isinstance(result, str)
    assert len(result) > 0


def test_handle_help(event_loop_for_test):
    result = event_loop_for_test.run_until_complete(handle_help("123"))
    assert isinstance(result, str)
    assert "/" in result


def test_handle_new_lot(event_loop_for_test):
    result = event_loop_for_test.run_until_complete(handle_new_lot("123", "Нужны стальные трубы 100 шт"))
    assert isinstance(result, str)
    assert len(result) > 0


def test_handle_new_lot_empty(event_loop_for_test):
    result = event_loop_for_test.run_until_complete(handle_new_lot("123", ""))
    assert isinstance(result, str)


def test_handle_status(event_loop_for_test):
    result = event_loop_for_test.run_until_complete(handle_status("123"))
    assert isinstance(result, str)
