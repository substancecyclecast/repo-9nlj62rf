# Telegram Bot Guide

## Overview

SnabAgent Telegram bot allows buyers to manage procurement lots directly from Telegram.

## Setup

### 1. Create Bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token

### 2. Configure

Add to `.env`:

```env
TELEGRAM_BOT_TOKEN=<your-bot-token>
SNABAGENT_API_BASE=https://your-domain:8000
```

### 3. Set Webhook

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain/api/v1/webhooks/telegram"}'
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and registration |
| `/new <description>` | Create a new procurement lot |
| `/status` | View your active lots |
| `/lot <id>` | Get details of a specific lot |
| `/help` | Show help message |

## Usage Examples

### Create a Lot

```
/new Нужны трубы стальные бесшовные ГОСТ 8732-78, 50 шт, диаметр 89 мм, срок 14 дней
```

Bot response:
```
✅ Лот создан: abc12345
Статус: draft
Отслеживайте: /lot abc12345
```

### Check Status

```
/status
```

Bot response:
```
📦 Ваши лоты:
• abc12345… — report_ready (metals)
• def67890… — sourcing (chemicals)
```

## Notifications

The bot can send automatic notifications:
- Lot ready for review
- Lot escalated (requires human attention)
- Daily digest summary

Configure notification preferences in the Streamlit admin panel.

## Architecture

```
Telegram → Webhook → FastAPI → SnabAgent API → Bot Handler → Response
```

The bot uses the same API endpoints as the web UI, authenticated via API key.
