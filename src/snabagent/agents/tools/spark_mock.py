"""Мок СПАРК-Интерфакс: ищем поставщиков по ОКВЭД и проверяем ИНН."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[4] / "data" / "suppliers_seed.csv"


@lru_cache(maxsize=1)
def _load() -> list[dict]:
    if not DATA.exists():
        return []
    with DATA.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


async def search_by_okved(okveds: list[str], region: str | None = None) -> list[dict]:
    rows = _load()
    res: list[dict] = []
    for r in rows:
        codes = (r.get("okved_codes") or "").split("|")
        if any(o in codes for o in okveds):
            if region and r.get("region") != region:
                continue
            res.append(
                {
                    "inn": r["inn"],
                    "ogrn": r.get("ogrn"),
                    "name": r["name"],
                    "website": r.get("website"),
                    "contact_email": r.get("contact_email"),
                    "region": r.get("region"),
                    "okved_codes": codes,
                    "categories": r.get("categories"),
                    "historical_score": float(r["historical_score"]) if r.get("historical_score") else None,
                    "source": "spark",
                }
            )
    return res


async def check_inn_ogrn(inn: str) -> dict | None:
    for r in _load():
        if r["inn"] == inn:
            return {
                "inn": inn,
                "ogrn": r.get("ogrn"),
                "name": r["name"],
                "active": True,
                "registered_at": "2010-01-01",
            }
    return None


CATEGORY_TO_OKVED = {
    "metals": ["27.10", "24.10", "46.72"],
    "it": ["46.51", "62.09", "26.20"],
    "mro": ["46.74", "47.52"],
    "consumables": ["46.49", "47.78"],
    "chemistry": ["20.13", "20.16"],
    "services": ["71.12", "70.22"],
}
