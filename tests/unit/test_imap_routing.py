"""Unit-test для умной маршрутизации входящих писем (P0-3)."""
from __future__ import annotations

import pytest

from snabagent.email_service.imap_poller import (
    _LOT_SUBJECT_RE,
    _LOT_TO_RE,
    _resolve_lot_id,
)


def test_to_regex_extracts_uuid():
    m = _LOT_TO_RE.search("lot+12345678-1234-1234-1234-1234567890ab@snabagent")
    assert m is not None
    assert m.group(1) == "12345678-1234-1234-1234-1234567890ab"


def test_to_regex_case_insensitive():
    m = _LOT_TO_RE.search("LOT+aabbccdd@x")
    assert m is not None
    assert m.group(1) == "aabbccdd"


def test_subject_regex_extracts_short_id():
    m = _LOT_SUBJECT_RE.search("Re: КП #LOT-aabbccdd Поставка")
    assert m is not None
    assert m.group(1) == "aabbccdd"


def test_subject_regex_case_insensitive():
    m = _LOT_SUBJECT_RE.search("re: #lot-DEADBEEF answer")
    assert m is not None
    assert m.group(1).lower() == "deadbeef"


@pytest.mark.asyncio
async def test_resolve_from_to_header():
    parsed = {
        "to": ["lot+12345678-1234-1234-1234-1234567890ab@snabagent.example"],
        "subject": "re: any",
    }
    lot_id = await _resolve_lot_id(parsed)
    assert lot_id == "12345678-1234-1234-1234-1234567890ab"


@pytest.mark.asyncio
async def test_resolve_returns_none_when_nothing_matches():
    parsed = {"to": ["x@y"], "subject": "просто письмо"}
    lot_id = await _resolve_lot_id(parsed)
    assert lot_id is None
