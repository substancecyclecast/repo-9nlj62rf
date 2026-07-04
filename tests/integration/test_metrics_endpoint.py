"""Integration: /metrics возвращает Prometheus text format."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from snabagent.api.main import app


@pytest.mark.asyncio
async def test_metrics_returns_prometheus_text():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    body = r.text
    # Наши метрики должны присутствовать
    assert "snabagent_http_requests_total" in body or "snabagent_lots_created_total" in body
