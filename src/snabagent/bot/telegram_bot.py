"""Telegram bot for SnabAgent buyers.

Commands:
  /start  — приветствие и регистрация
  /new    — создать новый лот
  /status — статус текущих лотов
  /lot <id> — детали лота
  /approve <id> — одобрить лот (если есть права)
  /escalate <id> — эскалация лота вручную

Использует webhook mode для интеграции с API.
Поддерживает эскалации: уведомления о лотах, требующих внимания.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API_BASE = os.environ.get("SNABAGENT_API_BASE", "http://localhost:8000")
API_KEY = os.environ.get("SNABAGENT_API_KEY", "dev-only-key-change-in-prod")
ESCALATION_CHAT_ID = os.environ.get("TELEGRAM_ESCALATION_CHAT_ID", "")

_HELP_TEXT = """🏗️ *SnabAgent Bot*

Доступные команды:
/start — приветствие
/new <описание> — создать новый лот
/status — статус ваших лотов
/lot <id> — детали конкретного лота
/approve <id> — одобрить лот
/escalate <id> — эскалировать лот
/help — эта справка

Бот работает в связке с SnabAgent API.
"""

_WELCOME_TEXT = """Привет! Я бот SnabAgent для управления закупками.

Используйте /new <описание заявки> для создания нового лота.
Используйте /status для просмотра текущих лотов.

Введите /help для полного списка команд.
"""


def _api_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


async def handle_start(chat_id: str) -> str:
    """Handle /start command."""
    return _WELCOME_TEXT


async def handle_help(chat_id: str) -> str:
    """Handle /help command."""
    return _HELP_TEXT


async def handle_new_lot(chat_id: str, description: str) -> str:
    """Handle /new command — create a new lot."""
    if not description.strip():
        return "Укажите описание заявки: /new <описание>"

    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=30, headers=_api_headers()) as client:
            resp = await client.post(
                "/api/v1/lots",
                json={
                    "customer_name": f"telegram_{chat_id}",
                    "raw_request": description,
                    "phase": "pre_nmck",
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                lot_id = data.get("id", "unknown")
                return f"✅ Лот создан: `{lot_id}`\nСтатус: {data.get('status', 'draft')}\n\nОтслеживайте: /lot {lot_id}"
            else:
                return f"❌ Ошибка создания лота: {resp.status_code}"
    except Exception as e:
        logger.error("Failed to create lot via API: %s", e)
        return f"❌ Ошибка подключения к API: {e}"


async def handle_status(chat_id: str) -> str:
    """Handle /status command — show lots status."""
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=15, headers=_api_headers()) as client:
            resp = await client.get("/api/v1/lots/", params={"page_size": 10})
            if resp.status_code == 200:
                data = resp.json()
                lots = data.get("items", data) if isinstance(data, dict) else data
                if not lots:
                    return "Нет активных лотов. Создайте новый: /new <описание>"

                lines = ["📦 *Ваши лоты:*\n"]
                for lot in lots[:10]:
                    status = lot.get("status", "unknown")
                    lot_id = lot.get("id", "?")[:8]
                    category = lot.get("category") or "—"
                    emoji = _status_emoji(status)
                    lines.append(f"{emoji} `{lot_id}…` — {status} ({category})")
                return "\n".join(lines)
            else:
                return f"❌ Ошибка получения лотов: {resp.status_code}"
    except Exception as e:
        logger.error("Failed to get lots: %s", e)
        return f"❌ Ошибка подключения к API: {e}"


async def handle_lot_detail(chat_id: str, lot_id: str) -> str:
    """Handle /lot <id> command — show lot details."""
    if not lot_id.strip():
        return "Укажите ID лота: /lot <id>"

    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=15, headers=_api_headers()) as client:
            resp = await client.get(f"/api/v1/lots/{lot_id}")
            if resp.status_code == 200:
                lot = resp.json()
                report = lot.get("final_report") or {}
                savings = report.get("savings_pct", "—")
                top3 = report.get("top_3", [])

                text = f"""📋 *Лот {lot_id[:8]}…*
Статус: {_status_emoji(lot.get('status', 'unknown'))} {lot.get('status', 'unknown')}
Категория: {lot.get('category', '—')}
Фаза: {lot.get('phase', '—')}
"""
                if lot.get("requires_human"):
                    text += "\n⚠️ *Требуется внимание человека!*\n"

                if top3:
                    text += f"\n💰 Экономия: {savings}%\n"
                    text += "\n*Топ-3 поставщика:*\n"
                    for i, s in enumerate(top3[:3], 1):
                        name = s.get("supplier", s.get("name", "?"))
                        price = s.get("total_price", s.get("price", "?"))
                        text += f"{i}. {name} — {price}\n"

                return text
            elif resp.status_code == 404:
                return f"Лот `{lot_id}` не найден."
            else:
                return f"❌ Ошибка: {resp.status_code}"
    except Exception as e:
        logger.error("Failed to get lot detail: %s", e)
        return f"❌ Ошибка подключения к API: {e}"


async def handle_approve(chat_id: str, lot_id: str) -> str:
    """Handle /approve <id> — approve a lot."""
    if not lot_id.strip():
        return "Укажите ID лота: /approve <id>"

    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=15, headers=_api_headers()) as client:
            resp = await client.post(
                f"/api/v1/lots/{lot_id}/approve",
                json={"supplier_id": None, "reviewer_comment": f"Approved via Telegram by chat {chat_id}"},
            )
            if resp.status_code == 200:
                return f"✅ Лот `{lot_id[:8]}…` одобрен."
            elif resp.status_code == 403:
                return "❌ Недостаточно прав для одобрения."
            else:
                return f"❌ Ошибка: {resp.status_code}"
    except Exception as e:
        logger.error("Failed to approve lot: %s", e)
        return f"❌ Ошибка: {e}"


async def handle_escalate(chat_id: str, lot_id: str) -> str:
    """Handle /escalate <id> — manually escalate a lot."""
    if not lot_id.strip():
        return "Укажите ID лота: /escalate <id>"

    # Send escalation notification
    await send_escalation_notification(lot_id, f"Manual escalation by chat {chat_id}")
    return f"⚠️ Лот `{lot_id[:8]}…` эскалирован. Ответственные уведомлены."


async def send_escalation_notification(lot_id: str, reason: str) -> None:
    """Send escalation notification to the configured chat."""
    if not BOT_TOKEN or not ESCALATION_CHAT_ID:
        logger.warning("Escalation notification skipped: TELEGRAM_BOT_TOKEN or ESCALATION_CHAT_ID not set")
        return

    text = f"""🚨 *ЭСКАЛАЦИЯ*

Лот: `{lot_id[:8]}…`
Причина: {reason}

Требуется вмешательство оператора.
Подробнее: /lot {lot_id}"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                url,
                json={"chat_id": ESCALATION_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            )
            logger.info("Escalation notification sent for lot %s", lot_id)
    except Exception as e:
        logger.error("Failed to send escalation notification: %s", e)


async def send_lot_status_update(lot_id: str, status: str, details: str = "") -> None:
    """Send lot status update to escalation chat (for important transitions)."""
    if not BOT_TOKEN or not ESCALATION_CHAT_ID:
        return

    important_statuses = {"report_ready", "escalated", "failed", "approved"}
    if status not in important_statuses:
        return

    emoji = _status_emoji(status)
    text = f"""{emoji} *Обновление лота*

Лот: `{lot_id[:8]}…`
Новый статус: {status}
{f'Детали: {details}' if details else ''}"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                url,
                json={"chat_id": ESCALATION_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            )
    except Exception as e:
        logger.error("Failed to send status update: %s", e)


def _status_emoji(status: str) -> str:
    """Map lot status to emoji."""
    return {
        "draft": "📝",
        "planned": "📋",
        "sourcing": "🔍",
        "rfq_sent": "📧",
        "responses_collected": "📥",
        "negotiating": "🤝",
        "verified": "✅",
        "report_ready": "📊",
        "approved": "👍",
        "rejected": "👎",
        "escalated": "🚨",
        "failed": "❌",
    }.get(status, "❓")
