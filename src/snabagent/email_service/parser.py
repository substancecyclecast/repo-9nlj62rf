"""Парсер входящих писем (RFC822)."""
from __future__ import annotations

import email
from email import policy
from email.header import decode_header
from email.parser import BytesParser
from typing import Any


def _decode(value: str | None) -> str:
    if not value:
        return ""
    return "".join(
        (b.decode(enc or "utf-8", errors="replace") if isinstance(b, bytes) else b)
        for b, enc in decode_header(value)
    )


def parse_inbound_email(raw: bytes) -> dict[str, Any]:
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    to_addrs = []
    if msg["To"]:
        for _, addr in email.utils.getaddresses([msg["To"]]):
            if addr:
                to_addrs.append(addr)
    body_text = ""
    body_html = ""
    attachments: list[dict] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = part.get_content_disposition()
            if disp == "attachment":
                attachments.append(
                    {
                        "filename": part.get_filename(),
                        "content_type": ctype,
                        "size_bytes": len(part.get_payload(decode=True) or b""),
                    }
                )
                continue
            if ctype == "text/plain" and not body_text:
                body_text = (part.get_content() or "").strip()
            elif ctype == "text/html" and not body_html:
                body_html = (part.get_content() or "").strip()
    else:
        body_text = (msg.get_content() or "").strip()

    refs = (msg["References"] or "").split() if msg["References"] else []
    return {
        "from": _decode(msg["From"]),
        "to": to_addrs,
        "subject": _decode(msg["Subject"]),
        "message_id": msg["Message-ID"],
        "in_reply_to": msg["In-Reply-To"],
        "references": refs,
        "body_text": body_text,
        "body_html": body_html,
        "attachments": attachments,
    }
