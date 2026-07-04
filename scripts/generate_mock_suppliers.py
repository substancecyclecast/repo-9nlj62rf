"""Генератор data/suppliers_seed.csv: 100 поставщиков + ингредиенты для исторических закупок."""
from __future__ import annotations

import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "suppliers_seed.csv"
OUT_HIST = Path(__file__).resolve().parents[1] / "data" / "historical_purchases.csv"

random.seed(42)

CATEGORY_TO_OKVED = {
    "metals": ["27.10", "24.10", "46.72"],
    "it": ["46.51", "62.09", "26.20"],
    "mro": ["46.74", "47.52"],
    "consumables": ["46.49", "47.78"],
    "chemistry": ["20.13", "20.16"],
    "services": ["71.12", "70.22"],
}
REGIONS = ["RU-77", "RU-78", "RU-50", "RU-52", "RU-66", "RU-23", "RU-16", "RU-74"]

# «Якорные» поставщики для золотого пути демо
ANCHOR = [
    ("7728168971", "1027700218800", 'ООО "Северсталь-Метиз"', "sales@severstal-metiz.example.ru",
     "https://severstal-metiz.example.ru", "metals", "RU-77"),
    ("7706107510", "1027700089118", 'ООО "Мечел-Сервис"', "opt@mechel-service.example.ru",
     "https://mechel-service.example.ru", "metals", "RU-78"),
    ("7728010001", "1027700089229", 'ООО "ММК Профиль"', "zakaz@mmk-profile.example.ru",
     "https://mmk-profile.example.ru", "metals", "RU-74"),
    ("7714016017", "1027739850962", 'ООО "Софтлайн Трейд"', "b2b@softline.example.ru",
     "https://softline.example.ru", "it", "RU-77"),
    ("7727290101", "1027739850123", 'ООО "Мерлион ИТ"', "sales@merlion.example.ru",
     "https://merlion.example.ru", "it", "RU-77"),
    ("7728168972", "1027700218456", 'ООО "СИБУР-Полимер"', "info@sibur-poly.example.ru",
     "https://sibur-poly.example.ru", "chemistry", "RU-66"),
    ("7728168973", "1027700218457", 'ООО "Казаньоргсинтез-Трейд"', "opt@kos-trade.example.ru",
     "https://kos-trade.example.ru", "chemistry", "RU-16"),
    ("7708168974", "1027700218458", 'ООО "ОФИС-ОПТ"', "zakaz@office-opt.example.ru",
     "https://office-opt.example.ru", "consumables", "RU-77"),
    ("7708168975", "1027700218459", 'ООО "ПрофСервис"', "sales@profservice.example.ru",
     "https://profservice.example.ru", "services", "RU-77"),
    ("7708168976", "1027700218460", 'ООО "МРО-Тех"', "sales@mro-tech.example.ru",
     "https://mro-tech.example.ru", "mro", "RU-77"),
]


def _rand_inn(used: set[str]) -> str:
    while True:
        candidate = str(random.randint(1_000_000_000, 9_999_999_999))
        if candidate not in used:
            used.add(candidate)
            return candidate


def _rand_ogrn(used: set[str]) -> str:
    while True:
        candidate = str(random.randint(10**12, 10**13 - 1))
        if candidate not in used:
            used.add(candidate)
            return candidate


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    inns: set[str] = set()
    ogrns: set[str] = set()
    rows: list[dict] = []
    # 1) якорные
    for inn, ogrn, name, email, web, cat, region in ANCHOR:
        inns.add(inn)
        ogrns.add(ogrn)
        rows.append(
            {
                "inn": inn,
                "ogrn": ogrn,
                "name": name,
                "short_name": name.replace("ООО ", "").strip('"'),
                "legal_address": f"г. Москва, ул. Тверская, д.{random.randint(1, 50)}",
                "contact_email": email,
                "contact_phone": f"+7495{random.randint(1000000, 9999999)}",
                "website": web,
                "okved_codes": "|".join(CATEGORY_TO_OKVED[cat]),
                "categories": cat,
                "region": region,
                "avg_response_time_hours": random.choice([4, 6, 8, 12]),
                "historical_score": round(random.uniform(0.78, 0.95), 2),
                "source": "anchor",
            }
        )
    # 2) синтетические
    name_pool = [
        "ТехноПром", "МетКомплект", "Спецтехнология", "Промторг", "ИндустрияГрупп",
        "ХимСнаб", "ОптМаркет", "БизнесСнаб", "СтальСервис", "ТехноЛогистика",
        "ИтТрэйд", "Сервис-М", "АльянсПром", "МеталлТраст", "ПолимерТрейд",
        "Софт-Импорт", "Профиль-Юг", "Технорум", "АктивСнаб", "ГлобалПром",
    ]
    for i in range(100 - len(ANCHOR)):
        cat = random.choice(list(CATEGORY_TO_OKVED.keys()))
        base = random.choice(name_pool)
        suffix = random.choice(["Групп", "Холдинг", "Компани", "Сервис", "Трейд", "Маркет"])
        full_name = f'ООО "{base}-{suffix}-{i+1}"'
        slug = f"{base.lower()}-{suffix.lower()}-{i+1}"
        inn = _rand_inn(inns)
        ogrn = _rand_ogrn(ogrns)
        rows.append(
            {
                "inn": inn,
                "ogrn": ogrn,
                "name": full_name,
                "short_name": f"{base}-{suffix}-{i+1}",
                "legal_address": f"г. {random.choice(['Москва', 'СПб', 'Казань', 'Челябинск', 'Екатеринбург'])}, "
                                 f"ул. {random.choice(['Промышленная', 'Заводская', 'Центральная'])}, д.{random.randint(1, 99)}",
                "contact_email": f"sales@{slug}.example.ru",
                "contact_phone": f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                "website": f"https://{slug}.example.ru",
                "okved_codes": "|".join(random.sample(CATEGORY_TO_OKVED[cat], k=min(2, len(CATEGORY_TO_OKVED[cat])))),
                "categories": cat,
                "region": random.choice(REGIONS),
                "avg_response_time_hours": random.choice([4, 8, 12, 24, 48]),
                "historical_score": round(random.uniform(0.4, 0.9), 2),
                "source": "seed",
            }
        )

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "inn",
                "ogrn",
                "name",
                "short_name",
                "legal_address",
                "contact_email",
                "contact_phone",
                "website",
                "okved_codes",
                "categories",
                "region",
                "avg_response_time_hours",
                "historical_score",
                "source",
            ],
        )
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} suppliers written to {OUT}")

    # Исторические закупки: связываем якорных поставщиков с типичными SKU.
    OUT_HIST.parent.mkdir(parents=True, exist_ok=True)
    history = []
    anchor_metal = [r for r in rows if r["categories"] == "metals" and r["source"] == "anchor"]
    anchor_it = [r for r in rows if r["categories"] == "it" and r["source"] == "anchor"]
    anchor_chem = [r for r in rows if r["categories"] == "chemistry" and r["source"] == "anchor"]
    anchor_cons = [r for r in rows if r["categories"] == "consumables" and r["source"] == "anchor"]
    anchor_mro = [r for r in rows if r["categories"] == "mro" and r["source"] == "anchor"]
    anchor_svc = [r for r in rows if r["categories"] == "services" and r["source"] == "anchor"]

    def add(supplier: dict, sku: str, qty: float, unit: str, price: float):
        history.append(
            {
                "supplier_inn": supplier["inn"],
                "nsi_sku": sku,
                "qty": qty,
                "unit": unit,
                "price_rub": price,
                "purchase_date": f"2025-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                "on_time": random.choice([True, True, True, False]),
                "quality_score": round(random.uniform(0.75, 0.98), 2),
            }
        )

    for sku, qty, unit, price in [
        ("MET-SHV-14-3PS", 8, "т", 52000),
        ("MET-ARM-A500C-12", 5, "т", 48000),
        ("MET-LIST-3-09Г2С", 6, "т", 76000),
        ("MET-LIST-3-3пс", 4, "т", 73000),
    ]:
        for s in anchor_metal:
            add(s, sku, qty, unit, price + random.randint(-1500, 1500))
    for sku in ["IT-LP-LENOVO-T14", "IT-LP-LENOVO-T16", "IT-SW-CISCO-9300", "IT-SW-ELTEX-MES-3324"]:
        for s in anchor_it:
            add(s, sku, 5, "шт", random.randint(100_000, 800_000))
    for sku in ["CHEM-PE-HDPE-273", "CHEM-PE-LDPE-153", "CHEM-PP-21030"]:
        for s in anchor_chem:
            add(s, sku, 15, "т", random.randint(85000, 115000))
    for sku in ["CONS-OFC-001", "CONS-OFC-002", "CONS-OFC-003"]:
        for s in anchor_cons:
            add(s, sku, 50, "шт", random.randint(200, 5000))
    for sku in ["MRO-PERCH-NIB-12", "MRO-SHRO-SF-1L"]:
        for s in anchor_mro:
            add(s, sku, 30, "шт", random.randint(900, 15000))
    for sku in ["SVC-DELIVERY-AUTO", "SVC-CLEAN-OFFICE-MONTH"]:
        for s in anchor_svc:
            add(s, sku, 1, "мес", random.randint(40000, 90000))

    with OUT_HIST.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["supplier_inn", "nsi_sku", "qty", "unit", "price_rub", "purchase_date", "on_time", "quality_score"],
        )
        w.writeheader()
        w.writerows(history)
    print(f"{len(history)} historical purchases written to {OUT_HIST}")


if __name__ == "__main__":
    main()
