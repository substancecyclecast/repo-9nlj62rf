"""Опциональный IMAP-поллер. Запускается отдельным процессом/сервисом.

Маршрутизирует входящие письма к лоту по:
1. To-адресу вида `lot+<uuid>@...`
2. Subject `[SnabAgent #LOT-<short_id>]`

Если ни одно не совпало — письмо сохраняется с `lot_id=None` (колонка nullable),
и попадает в очередь "unrouted" для ручного разбора.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime

from sqlalchemy import select

from ..db.models import Lot
from ..db.repositories import RfqEmailRepo
from ..db.session import AsyncSessionLocal
from ..settings import settings
from .parser import parse_inbound_email

log = logging.getLogger(__name__)

_LOT_TO_RE = re.compile(r"lot\+([a-f0-9\-]+)@", flags=re.IGNORECASE)
_LOT_SUBJECT_RE = re.compile(r"#LOT-([a-f0-9]+)", flags=re.IGNORECASE)


def _get_aioimaplib():
    """Ленивая загрузка aioimaplib (не критично для оффлайн-демо)."""
    try:
        import aioimaplib  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("aioimaplib не установлен. pip install aioimaplib") from e
    return aioimaplib


async def _resolve_lot_id(parsed: dict) -> str | None:
    """Пытается определить lot_id из To-headers или Subject."""
    for addr in parsed.get("to") or []:
        m = _LOT_TO_RE.search(addr)
        if m:
            return m.group(1)
    subject = parsed.get("subject") or ""
    m = _LOT_SUBJECT_RE.search(subject)
    if m:
        short = m.group(1)
        async with AsyncSessionLocal() as s:
            q = select(Lot).where(Lot.id.like(f"{short}%"))
            lot = (await s.execute(q)).scalars().first()
            if lot:
                return str(lot.id)
    return None


async def poll_loop(stop_event: asyncio.Event | None = None) -> None:
    while True:
        if stop_event and stop_event.is_set():
            break
        try:
            await _poll_once()
        except Exception as e:  # pragma: no cover
            log.exception("IMAP poll error: %s", e)
        await asyncio.sleep(settings.imap_poll_interval_sec)


async def _poll_once() -> None:
    aioimaplib = _get_aioimaplib()
    if settings.imap_use_ssl:
        client = aioimaplib.IMAP4_SSL(host=settings.imap_host, port=settings.imap_port)
    else:
        client = aioimaplib.IMAP4(host=settings.imap_host, port=settings.imap_port)
    await client.wait_hello_from_server()
    await client.login(settings.imap_user, settings.imap_password.get_secret_value())
    await client.select("INBOX")
    response = await client.uid_search("UNSEEN")
    if not response.lines:
        await client.logout()
        return
    uids = response.lines[0].split()
    for uid in uids:
        msg_response = await client.uid("fetch", uid.decode(), "RFC822")
        if len(msg_response.lines) < 2:
            continue
        raw = msg_response.lines[1]
        parsed = parse_inbound_email(raw)
        lot_id = await _resolve_lot_id(parsed)
        if lot_id is None:
            log.warning(
                "IMAP poller: cannot route email subject=%r — saved as unrouted",
                parsed.get("subject"),
            )
        async with AsyncSessionLocal() as session:
            await RfqEmailRepo(session).create(
                lot_id=lot_id,
                direction="in",
                subject=parsed["subject"],
                body_text=parsed["body_text"],
                body_html=parsed["body_html"],
                message_id=parsed["message_id"],
                in_reply_to=parsed["in_reply_to"],
                references_ids=parsed["references"],
                attachments=parsed["attachments"],
                received_at=datetime.now(UTC),
            )
        await client.uid("store", uid.decode(), "+FLAGS", "(\\Seen)")
    await client.logout()
