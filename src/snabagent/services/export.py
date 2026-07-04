"""Export services: PDF report generation, CSV/JSON export for BI."""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def generate_lot_report_html(lot: Any, report: dict[str, Any]) -> str:
    """Generate HTML report for a single lot (for PDF conversion)."""
    top_3 = report.get("top_3", [])
    savings_pct = report.get("savings_pct", 0)

    rows_html = ""
    for i, s in enumerate(top_3, 1):
        name = s.get("supplier", s.get("name", "N/A"))
        price = s.get("total_price", s.get("price", "N/A"))
        delivery = s.get("delivery_days", "N/A")
        rows_html += f"<tr><td>{i}</td><td>{name}</td><td>{price}</td><td>{delivery}</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>SnabAgent Report — Lot {lot.id}</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
h1 {{ color: #0f172a; border-bottom: 2px solid #16a34a; padding-bottom: 8px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
th {{ background-color: #f0fdf4; color: #166534; }}
.meta {{ color: #666; font-size: 0.9em; }}
.savings {{ font-size: 1.2em; color: #16a34a; font-weight: bold; }}
</style>
</head>
<body>
<h1>SnabAgent — Отчёт по лоту</h1>
<p class="meta">ID лота: {lot.id}</p>
<p class="meta">Категория: {getattr(lot, 'category', 'N/A') or 'N/A'}</p>
<p class="meta">Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
<p class="savings">Экономия: {savings_pct:.1f}%</p>

<h2>Топ-3 поставщика</h2>
<table>
<tr><th>#</th><th>Поставщик</th><th>Цена</th><th>Срок (дней)</th></tr>
{rows_html}
</table>

<h2>Рекомендация</h2>
<p>{report.get('recommendation', 'Рекомендация не сформирована.')}</p>

<hr>
<p class="meta">Сгенерировано SnabAgent v1.0</p>
</body>
</html>"""


def lots_to_csv(lots: list[dict[str, Any]]) -> str:
    """Convert list of lot dicts to CSV string."""
    if not lots:
        return ""

    output = io.StringIO()
    fieldnames = [
        "id", "status", "category", "phase", "customer_id",
        "total_estimated_rub", "created_at", "updated_at", "closed_at",
        "requires_human", "escalation_reason",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for lot in lots:
        writer.writerow(lot)
    return output.getvalue()


def lots_to_jsonl(lots: list[dict[str, Any]]) -> str:
    """Convert list of lot dicts to JSON Lines format."""
    lines = []
    for lot in lots:
        serializable = {}
        for k, v in lot.items():
            if isinstance(v, datetime):
                serializable[k] = v.isoformat()
            else:
                serializable[k] = v
        lines.append(json.dumps(serializable, ensure_ascii=False))
    return "\n".join(lines)
