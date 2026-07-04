"""Daily email digest for buyers: summary of lots requiring attention."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DIGEST_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f8fafc; }}
.container {{ max-width: 600px; margin: 0 auto; background: white;
  border-radius: 8px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
h1 {{ color: #0f172a; font-size: 20px; }}
.stat {{ display: inline-block; margin: 8px 16px 8px 0; padding: 8px 16px; background: #f0fdf4; border-radius: 6px; }}
.stat-num {{ font-size: 24px; font-weight: bold; color: #16a34a; }}
.stat-label {{ font-size: 12px; color: #666; }}
.btn {{ display: inline-block; padding: 10px 20px; background: #16a34a;
  color: white; text-decoration: none; border-radius: 6px; margin-top: 16px; }}
.footer {{ margin-top: 24px; font-size: 12px; color: #999; border-top: 1px solid #eee; padding-top: 12px; }}
</style>
</head>
<body>
<div class="container">
<h1>SnabAgent — Ежедневная сводка</h1>
<p>Добрый день, {user_name}!</p>

<div>
<div class="stat"><div class="stat-num">{ready_count}</div><div class="stat-label">Готовы к ревью</div></div>
<div class="stat"><div class="stat-num">{processing_count}</div><div class="stat-label">В обработке</div></div>
<div class="stat"><div class="stat-num">{escalated_count}</div><div class="stat-label">Эскалированы</div></div>
</div>

<a href="{app_url}" class="btn">Открыть в SnabAgent</a>

<div class="footer">
<p>Вы получили это письмо, так как подписаны на дайджест SnabAgent.</p>
<p><a href="{unsubscribe_url}">Отписаться</a></p>
</div>
</div>
</body>
</html>"""


def render_digest_html(
    user_name: str,
    ready_count: int,
    processing_count: int,
    escalated_count: int,
    app_url: str = "http://localhost:8501",
    unsubscribe_url: str = "#",
) -> str:
    """Render the daily digest email HTML."""
    return DIGEST_HTML_TEMPLATE.format(
        user_name=user_name,
        ready_count=ready_count,
        processing_count=processing_count,
        escalated_count=escalated_count,
        app_url=app_url,
        unsubscribe_url=unsubscribe_url,
    )
