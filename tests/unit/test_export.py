"""Tests for export service."""
from __future__ import annotations

from snabagent.services.export import lots_to_csv, lots_to_jsonl


def test_lots_to_csv_empty():
    result = lots_to_csv([])
    assert isinstance(result, str)


def test_lots_to_csv_with_data():
    data = [
        {"id": "1", "status": "draft", "category": "Трубы"},
        {"id": "2", "status": "approved", "category": "Арматура"},
    ]
    result = lots_to_csv(data)
    assert "1" in result
    assert "2" in result
    assert "Трубы" in result


def test_lots_to_jsonl_empty():
    result = lots_to_jsonl([])
    assert isinstance(result, str)


def test_lots_to_jsonl_with_data():
    data = [
        {"id": "1", "status": "draft"},
        {"id": "2", "status": "approved"},
    ]
    result = lots_to_jsonl(data)
    lines = result.strip().split("\n")
    assert len(lines) == 2
