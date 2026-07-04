"""Webhook от Mailcow / n8n для inbound писем."""
from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from ...db.repositories import RfqEmailRepo
from ...db.session import AsyncSessionLocal
from ...email_service.parser import parse_inbound_email

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

LOT_RE = re.compile(r"lot\+([a-f0-9\-]+)@", flags=re.IGNORECASE)
SUBJECT_LOT_RE = re.compile(r"#LOT-([a-f0-9]+)", flags=re.IGNORECASE)


@router.post("/email-in")
async def email_in(request: Request):
    raw = await request.body()
    parsed = parse_inbound_email(raw)
    lot_id = None
    for addr in parsed.get("to", []) or []:
        m = LOT_RE.search(addr)
        if m:
            lot_id = m.group(1)
            break
    if not lot_id and parsed.get("subject"):
        m = SUBJECT_LOT_RE.search(parsed["subject"])
        if m:
            short = m.group(1)
            from sqlalchemy import select

            from ...db.models import Lot

            async with AsyncSessionLocal() as s:
                q = select(Lot).where(Lot.id.like(f"{short}%"))
                lot = (await s.execute(q)).scalars().first()
                if lot:
                    lot_id = str(lot.id)
    if not lot_id:
        raise HTTPException(422, detail="Cannot route email to lot")

    async with AsyncSessionLocal() as s:
        await RfqEmailRepo(s).create(
            lot_id=lot_id,
            direction="in",
            subject=parsed.get("subject"),
            body_text=parsed.get("body_text"),
            body_html=parsed.get("body_html"),
            message_id=parsed.get("message_id"),
            in_reply_to=parsed.get("in_reply_to"),
            references_ids=parsed.get("references") or [],
            attachments=parsed.get("attachments") or [],
            received_at=datetime.now(UTC),
        )
    return {"ok": True, "lot_id": lot_id}
