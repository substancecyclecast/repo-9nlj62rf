"""Historical price learning: predict optimal price from past lots."""
from __future__ import annotations

import logging
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def predict_price(
    session: AsyncSession,
    category: str,
    months: int = 12,
) -> dict[str, Any] | None:
    """Predict price based on historical data for a category.

    Uses median price from closed lots in the last N months.
    Returns None if insufficient data.
    """
    from ..db.models import Lot, LotStatus

    cutoff = datetime.now(UTC) - timedelta(days=months * 30)

    stmt = (
        select(Lot.total_estimated_rub)
        .where(
            Lot.category == category,
            Lot.status == LotStatus.approved,
            Lot.closed_at is not None,
            Lot.closed_at >= cutoff,
            Lot.total_estimated_rub is not None,
        )
    )
    result = await session.execute(stmt)
    prices = [float(row[0]) for row in result.fetchall() if row[0] is not None]

    if len(prices) < 3:
        return None

    median_price = statistics.median(prices)
    mean_price = statistics.mean(prices)
    stdev = statistics.stdev(prices) if len(prices) > 1 else 0.0

    return {
        "predicted_price": round(median_price, 2),
        "mean_price": round(mean_price, 2),
        "stdev": round(stdev, 2),
        "sample_size": len(prices),
        "period_months": months,
        "category": category,
    }
