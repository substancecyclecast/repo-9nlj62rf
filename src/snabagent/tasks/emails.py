"""Celery-задачи для IMAP-поллинга."""
from __future__ import annotations

import asyncio
import logging

from celery import shared_task

from ..email_service.imap_poller import _poll_once

log = logging.getLogger(__name__)


@shared_task(name="snabagent.tasks.emails.poll_inbox")
def poll_inbox_task() -> None:
    try:
        asyncio.run(_poll_once())
    except Exception as e:  # pragma: no cover
        log.warning("imap poll failed: %s", e)
