"""Генерирует data/sample_excel/import_metals.xlsx с тестовыми данными.

Запуск:
    python scripts/generate_sample_excel.py
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_excel"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Заявка"
    ws.append(["Наименование", "Количество", "Ед.изм", "Срок дней", "Примечание"])
    ws.append(["Швеллер 14 ст3пс ГОСТ 8240-97", 10, "т", 7, "обычная партия"])
    ws.append(["Арматура А500С диаметр 12", 5, "т", 7, ""])
    ws.append(["Лист 3мм 09Г2С", 8, "т", 7, "к среде"])
    out = OUT_DIR / "import_metals.xlsx"
    wb.save(out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
