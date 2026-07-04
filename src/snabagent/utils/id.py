"""Короткий человекочитаемый ID лота (8 hex-символов)."""
from __future__ import annotations

from uuid import UUID


def short_lot_id(lot_id: str | UUID) -> str:
    s = str(lot_id).replace("-", "")
    return s[:8]
