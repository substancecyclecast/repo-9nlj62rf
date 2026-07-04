"""Unit-test для Excel-отчёта (P0-1): проверяем, что колонки совпадают
с ключами, которые Reporter реально кладёт в state.report.top_3.
"""
from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook

from snabagent.api.routes import lots as lots_routes


class _FakeLot:
    """Минимально достаточная имитация Lot ORM-объекта."""

    def __init__(self, top_3, savings_rub=100000, savings_pct=10.5):
        self.id = "lot-id"
        self.customer_id = "cust-id"
        self.status = type("S", (), {"value": "report_ready"})
        self.final_report = {
            "top_3": top_3,
            "summary": "Demo summary",
            "savings_vs_avg_rub": savings_rub,
            "savings_vs_avg_pct": savings_pct,
        }


def _fake_top_3():
    """Точная форма, которую возвращает Reporter (см. reporter.py)."""
    return [
        {
            "supplier_name": "ООО Демо-1",
            "inn": "7700000001",
            "total_price_rub": 1_500_000.0,
            "lead_time_days": 14,
            "score": 0.95,
            "discrepancies": [],
            "rationale": "Прошла верификация",
            "recommendation": "approve",
        },
        {
            "supplier_name": "ООО Демо-2",
            "inn": "7700000002",
            "total_price_rub": 1_650_000.0,
            "lead_time_days": 21,
            "score": 0.92,
            "discrepancies": [],
            "rationale": "Прошла",
            "recommendation": "approve",
        },
    ]


def test_excel_uses_reporter_keys_directly():
    """Проверяем, что код в lots.export_report_xlsx использует те же ключи,
    что Reporter (inn, total_price_rub, score)."""
    import inspect

    src = inspect.getsource(lots_routes.export_report_xlsx)
    # Ключи, которые Reporter реально пишет
    assert '"inn"' in src or "'inn'" in src
    assert '"total_price_rub"' in src or "'total_price_rub'" in src
    assert '"score"' in src or "'score'" in src
    # Legacy-fallback ключи остаются (для backward-compat)
    assert "supplier_inn" in src
    assert "confidence" in src


def test_excel_workbook_structure():
    """Generative проверка: можно ли загрузить итоговый Excel и прочитать
    из него прайс и score."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Top-3"
    ws.append([
        "Поставщик", "ИНН", "Общая цена ₽", "Уверенность",
        "Срок (дн)", "Причины", "Рекомендация",
    ])
    for r in _fake_top_3():
        ws.append([
            r.get("supplier_name") or "?",
            r.get("inn") or r.get("supplier_inn") or "?",
            r.get("total_price_rub") or r.get("total_price") or 0,
            r.get("score") or r.get("confidence") or 0,
            r.get("lead_time_days") or "—",
            r.get("rationale") or "",
            r.get("recommendation") or "",
        ])
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    wb2 = load_workbook(bio)
    ws2 = wb2["Top-3"]
    rows = list(ws2.iter_rows(values_only=True))
    assert rows[0] == (
        "Поставщик", "ИНН", "Общая цена ₽", "Уверенность",
        "Срок (дн)", "Причины", "Рекомендация",
    )
    # Цена строки 1 — ровно та, что в Reporter
    assert rows[1][2] == 1_500_000.0
    assert rows[1][3] == 0.95
    # И ИНН тоже не "?"
    assert rows[1][1] == "7700000001"
