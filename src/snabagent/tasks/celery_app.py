"""Celery-приложение: фоновый прогон лотов, IMAP-поллинг, и периодические задачи."""
from __future__ import annotations

from celery import Celery

from ..settings import settings

celery_app = Celery(
    "snabagent",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_routes={
        "snabagent.tasks.lot_pipeline.*": {"queue": "lots"},
        "snabagent.tasks.emails.*": {"queue": "emails"},
    },
    beat_schedule={
        "imap-poll": {
            "task": "snabagent.tasks.emails.poll_inbox",
            "schedule": settings.imap_poll_interval_sec,
        },
        "recover-stuck-lots": {
            "task": "snabagent.tasks.lot_pipeline.recover_stuck_lots",
            "schedule": 600,  # every 10 minutes
        },
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Import task modules so Celery autodiscovers them
from .emails import *  # noqa: E402,F401,F403
from .lot_pipeline import *  # noqa: E402,F401,F403
