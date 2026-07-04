"""Запуск лота через Celery с retry, backoff, и DLQ для неудачных задач."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from ..agents import run_lot
from ..db.repositories import LotRepo
from ..db.session import AsyncSessionLocal

log = logging.getLogger(__name__)

# Dead Letter Queue key in Redis
DLQ_KEY = "snabagent:dlq:lot_pipeline"


@shared_task(
    name="snabagent.tasks.lot_pipeline.run_lot",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_lot_task(self, lot_id: str) -> None:
    try:
        asyncio.run(_run(lot_id))
    except Exception as e:
        log.warning("run_lot_task attempt %d failed for lot_id=%s: %s", self.request.retries + 1, lot_id, e)
        try:
            self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            log.error("run_lot_task DLQ: lot_id=%s exhausted retries", lot_id)
            asyncio.run(_mark_failed(lot_id, str(e)))
            _push_to_dlq(lot_id, str(e))


@shared_task(
    name="snabagent.tasks.lot_pipeline.recover_stuck_lots",
    bind=True,
    max_retries=1,
)
def recover_stuck_lots(self) -> None:
    """Periodic task: find lots stuck in intermediate status >30 min and re-queue."""
    asyncio.run(_recover_stuck())


async def _run(lot_id: str) -> None:
    async with AsyncSessionLocal() as s:
        lot = await LotRepo(s).get(lot_id)
        if not lot:
            return
        state = {
            "lot_id": str(lot.id),
            "customer_id": str(lot.customer_id),
            "raw_request": lot.raw_request,
            "phase": lot.phase.value if lot.phase else "pre_nmck",
            "status": "draft",
        }
    await run_lot(state)


async def _mark_failed(lot_id: str, error: str) -> None:
    """Mark lot as failed after all retries exhausted."""
    from ..db.models import LotStatus

    async with AsyncSessionLocal() as s:
        await LotRepo(s).update_status(lot_id, LotStatus.failed, error_detail=error)


async def _recover_stuck() -> None:
    """Find lots stuck in intermediate statuses for >30 minutes and re-enqueue them."""
    from ..db.models import LotStatus

    stuck_statuses = [LotStatus.draft, LotStatus.sourcing, LotStatus.rfq_sent, LotStatus.negotiating]
    threshold = datetime.now(UTC).timestamp() - 1800  # 30 minutes ago

    async with AsyncSessionLocal() as s:
        from sqlalchemy import select

        from ..db.models import Lot

        for status in stuck_statuses:
            q = select(Lot).where(Lot.status == status)
            lots = list((await s.execute(q)).scalars().all())
            for lot in lots:
                if lot.updated_at and lot.updated_at.timestamp() < threshold:
                    log.info("Recovering stuck lot %s (status=%s)", lot.id, status.value)
                    run_lot_task.delay(str(lot.id))


def _push_to_dlq(lot_id: str, error: str) -> None:
    """Push failed lot to Dead Letter Queue in Redis."""
    try:
        import json

        import redis as redis_lib

        from ..settings import settings

        r = redis_lib.from_url(settings.redis_url)
        r.rpush(
            DLQ_KEY,
            json.dumps({"lot_id": lot_id, "error": error, "ts": datetime.now(UTC).isoformat()}),
        )
    except Exception as e:
        log.error("Failed to push to DLQ: %s", e)
