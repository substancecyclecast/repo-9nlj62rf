"""Health-check endpoints for Kubernetes liveness/readiness probes."""
from __future__ import annotations

import logging

from fastapi import APIRouter

from ...settings import settings

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health/live")
async def liveness():
    """Liveness probe: always returns 200 if the process is running."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness():
    """Readiness probe: checks PostgreSQL, Redis, Qdrant connectivity."""
    components: dict[str, str] = {}
    overall = "healthy"

    # Check PostgreSQL
    try:
        from sqlalchemy import text

        from ...db.session import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        components["postgres"] = "ok"
    except Exception as e:
        logger.warning("Health check: PostgreSQL unavailable: %s", e)
        components["postgres"] = f"error: {e}"
        overall = "degraded"

    # Check Redis
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        components["redis"] = "ok"
    except Exception as e:
        logger.warning("Health check: Redis unavailable: %s", e)
        components["redis"] = f"error: {e}"
        overall = "degraded"

    # Check Qdrant
    try:
        from qdrant_client import QdrantClient

        qc = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        qc.get_collections()
        qc.close()
        components["qdrant"] = "ok"
    except Exception as e:
        logger.warning("Health check: Qdrant unavailable: %s", e)
        components["qdrant"] = f"error: {e}"
        overall = "degraded"

    status_code = 200 if overall == "healthy" else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={"status": overall, "components": components},
        status_code=status_code,
    )
