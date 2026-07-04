"""Prometheus /metrics endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Response

from ..metrics import metrics_endpoint

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics():
    payload, content_type = metrics_endpoint()
    return Response(content=payload, media_type=content_type)
