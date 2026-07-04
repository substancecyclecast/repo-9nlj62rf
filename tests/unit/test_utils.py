"""Tests for utility modules."""
from __future__ import annotations

import uuid

from snabagent.utils.id import short_lot_id
from snabagent.utils.retry import default_retrying
from snabagent.utils.time import utcnow


def test_short_lot_id_from_str():
    uid = str(uuid.uuid4())
    short = short_lot_id(uid)
    assert len(short) == 8
    assert short == uid.replace("-", "")[:8]


def test_short_lot_id_from_uuid():
    uid = uuid.uuid4()
    short = short_lot_id(uid)
    assert len(short) == 8


def test_utcnow():
    ts = utcnow()
    assert ts.tzinfo is not None


def test_default_retrying():
    r = default_retrying(max_attempts=2)
    assert r is not None
