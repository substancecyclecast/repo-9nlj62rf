"""Tests for the price prediction module."""
from __future__ import annotations

import pytest

from snabagent.db.session import AsyncSessionLocal
from snabagent.services.price_predictor import predict_price


@pytest.mark.asyncio
async def test_predict_price_no_data():
    """With no historical lots, predict_price returns None."""
    async with AsyncSessionLocal() as session:
        result = await predict_price(session, "nonexistent_category_xyz")
        assert result is None


@pytest.mark.asyncio
async def test_predict_price_returns_dict_or_none():
    """predict_price returns a dict with required keys or None."""
    async with AsyncSessionLocal() as session:
        result = await predict_price(session, "Трубы стальные")
        if result is not None:
            assert "predicted_price" in result
            assert "mean_price" in result
            assert "sample_size" in result
            assert "category" in result
            assert result["predicted_price"] >= 0


@pytest.mark.asyncio
async def test_predict_price_custom_months():
    """predict_price accepts months parameter."""
    async with AsyncSessionLocal() as session:
        result = await predict_price(session, "test", months=1)
        assert result is None  # no data in test DB
