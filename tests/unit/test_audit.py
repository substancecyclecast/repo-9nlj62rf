"""Tests for audit logger utilities."""
from __future__ import annotations

from snabagent.audit.logger import _mask_value


def test_mask_value_string():
    result = _mask_value("hello world")
    assert isinstance(result, str)


def test_mask_value_dict():
    result = _mask_value({"key": "value", "nested": {"a": "b"}})
    assert isinstance(result, dict)
    assert "key" in result
    assert "nested" in result


def test_mask_value_list():
    result = _mask_value(["a", "b", "c"])
    assert isinstance(result, list)
    assert len(result) == 3


def test_mask_value_number():
    assert _mask_value(42) == 42
    assert _mask_value(3.14) == 3.14


def test_mask_value_none():
    assert _mask_value(None) is None
