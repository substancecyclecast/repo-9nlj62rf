"""Отправка тестового RFQ через SMTP/dump-режим. Используется для smoke-теста почты."""
from __future__ import annotations

import asyncio

from snabagent.email_service.sender import send_rfq_email


async def main():
    msg_id = await send_rfq_email(
        supplier_email="opt@example-supplier.ru",
        subject="[SnabAgent #LOT-test] Запрос КП",
        body="Тестовое письмо\n\nС уважением,\nSnabAgent",
        reply_to="lot+test@demo.snabagent.ru",
    )
    print(f"Sent message id: {msg_id}")


if __name__ == "__main__":
    asyncio.run(main())
