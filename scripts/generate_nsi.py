"""Генератор data/nsi_sample.csv: 200 позиций в 6 категориях с устойчивым seed=42."""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "nsi_sample.csv"

random.seed(42)


def metals() -> list[dict]:
    rows: list[dict] = []
    grades = ["3пс", "09Г2С", "Ст3сп", "Ст20", "5ХНМ"]
    # Швеллеры
    for size in [10, 12, 14, 16, 18, 20, 22, 24, 27, 30]:
        rows.append(
            dict(
                sku=f"MET-SHV-{size}-3PS",
                name=f"Швеллер {size} ст3пс",
                full_name=f"Швеллер стальной горячекатаный №{size} ст3пс ГОСТ 8240-97",
                category="metals",
                unit="т",
                gost="ГОСТ 8240-97",
                typical_price_rub=50000 + size * 200,
                attributes={"steel_grade": "3пс", "size_no": str(size), "type": "shveller"},
            )
        )
    # Арматура
    for d in [8, 10, 12, 14, 16, 18, 20, 22, 25, 28]:
        rows.append(
            dict(
                sku=f"MET-ARM-A500C-{d}",
                name=f"Арматура А500С d{d}",
                full_name=f"Арматура стальная рифлёная А500С диам.{d} ГОСТ 34028-2016",
                category="metals",
                unit="т",
                gost="ГОСТ 34028-2016",
                typical_price_rub=46000 + d * 100,
                attributes={"class": "A500C", "diameter_mm": d},
            )
        )
    # Листы
    for th in [2, 3, 4, 5, 6, 8, 10, 12, 14, 16]:
        gr = random.choice(grades)
        rows.append(
            dict(
                sku=f"MET-LIST-{th}-{gr}",
                name=f"Лист {th} {gr}",
                full_name=f"Лист горячекатаный {th}мм сталь {gr} ГОСТ 19281-2014",
                category="metals",
                unit="т",
                gost="ГОСТ 19281-2014",
                typical_price_rub=70000 + th * 1500,
                attributes={"thickness_mm": th, "steel_grade": gr},
            )
        )
    # Уголки/трубы — добавим разнообразия
    for s in [25, 32, 40, 50, 63, 75]:
        rows.append(
            dict(
                sku=f"MET-UGL-{s}-3PS",
                name=f"Уголок {s}x{s} ст3пс",
                full_name=f"Уголок стальной горячекатаный равнополочный {s}x{s} ст3пс ГОСТ 8509-93",
                category="metals",
                unit="т",
                gost="ГОСТ 8509-93",
                typical_price_rub=55000 + s * 200,
                attributes={"steel_grade": "3пс", "wing_mm": s, "type": "ugolok"},
            )
        )
    for d in [20, 25, 32, 40, 50, 76, 89, 108, 159]:
        rows.append(
            dict(
                sku=f"MET-PIPE-{d}-Ст20",
                name=f"Труба ВГП {d}",
                full_name=f"Труба стальная ВГП водогазопроводная {d}х3.2 ст.20 ГОСТ 3262-75",
                category="metals",
                unit="т",
                gost="ГОСТ 3262-75",
                typical_price_rub=60000 + d * 100,
                attributes={"diameter_mm": d, "steel_grade": "Ст20", "type": "pipe_vgp"},
            )
        )
    return rows


def it_items() -> list[dict]:
    rows: list[dict] = []
    rows += [
        dict(
            sku="IT-LP-LENOVO-T14",
            name="Ноутбук Lenovo ThinkPad T14",
            full_name="Ноутбук Lenovo ThinkPad T14 Gen 4 Core i5 16GB 512SSD",
            category="it",
            unit="шт",
            gost="",
            typical_price_rub=135000,
            attributes={"brand": "Lenovo", "model": "T14", "ram_gb": 16, "ssd_gb": 512},
        ),
        dict(
            sku="IT-LP-LENOVO-T16",
            name="Ноутбук Lenovo ThinkPad T16",
            full_name="Ноутбук Lenovo ThinkPad T16 Gen 2 Core i7 32GB 1TB",
            category="it",
            unit="шт",
            gost="",
            typical_price_rub=185000,
            attributes={"brand": "Lenovo", "model": "T16", "ram_gb": 32, "ssd_gb": 1024},
        ),
        dict(
            sku="IT-LP-HP-840",
            name="Ноутбук HP EliteBook 840",
            full_name="Ноутбук HP EliteBook 840 G10 Core i5 16GB 512SSD",
            category="it",
            unit="шт",
            gost="",
            typical_price_rub=132000,
            attributes={"brand": "HP", "model": "EliteBook 840", "ram_gb": 16, "ssd_gb": 512},
        ),
        dict(
            sku="IT-SW-CISCO-9300",
            name="Коммутатор Cisco Catalyst 9300",
            full_name="Коммутатор Cisco Catalyst 9300 48-port",
            category="it",
            unit="шт",
            gost="",
            typical_price_rub=820000,
            attributes={"brand": "Cisco", "model": "C9300-48", "ports": 48},
        ),
        dict(
            sku="IT-SW-ELTEX-MES-3324",
            name="Коммутатор Eltex MES3324",
            full_name="Коммутатор Eltex MES3324F 24x1G + 4x10G uplink",
            category="it",
            unit="шт",
            gost="",
            typical_price_rub=295000,
            attributes={"brand": "Eltex", "model": "MES3324F", "ports": 28},
        ),
        dict(
            sku="IT-SRV-DELL-R650",
            name="Сервер Dell PowerEdge R650",
            full_name="Сервер Dell PowerEdge R650 2xXeon Gold 6338 256GB",
            category="it",
            unit="шт",
            gost="",
            typical_price_rub=1450000,
            attributes={"brand": "Dell", "model": "R650"},
        ),
        dict(
            sku="IT-MON-DELL-P2723",
            name="Монитор Dell P2723QE 27\"",
            full_name="Монитор Dell P2723QE 27\" 4K USB-C Hub",
            category="it",
            unit="шт",
            gost="",
            typical_price_rub=58000,
            attributes={"brand": "Dell", "model": "P2723QE", "diagonal_in": 27},
        ),
        dict(
            sku="IT-KBM-LOGI-K780",
            name="Клавиатура Logitech K780",
            full_name="Клавиатура Logitech K780 Multi-Device Wireless",
            category="it",
            unit="шт",
            gost="",
            typical_price_rub=7800,
            attributes={"brand": "Logitech", "model": "K780"},
        ),
    ]
    return rows


def mro_items() -> list[dict]:
    rows = []
    rows += [
        dict(
            sku="MRO-PERCH-NIB-12",
            name="Перчатки нитриловые M",
            full_name="Перчатки нитриловые без пудры размер M, 100шт/упак",
            category="mro",
            unit="упак",
            gost="",
            typical_price_rub=950,
            attributes={"size": "M", "qty_per_pack": 100},
        ),
        dict(
            sku="MRO-PERCH-NIB-L",
            name="Перчатки нитриловые L",
            full_name="Перчатки нитриловые без пудры размер L, 100шт/упак",
            category="mro",
            unit="упак",
            gost="",
            typical_price_rub=970,
            attributes={"size": "L", "qty_per_pack": 100},
        ),
        dict(
            sku="MRO-SHRO-SF-1L",
            name="Шуруповёрт SHF-1L",
            full_name="Шуруповёрт аккум. 18В 2x4Ач кейс",
            category="mro",
            unit="шт",
            gost="",
            typical_price_rub=12500,
            attributes={"voltage_v": 18},
        ),
        dict(
            sku="MRO-DRILL-BOSCH-GBH",
            name="Перфоратор Bosch GBH",
            full_name="Перфоратор Bosch GBH 2-28 SDS-plus 880Вт",
            category="mro",
            unit="шт",
            gost="",
            typical_price_rub=24800,
            attributes={"brand": "Bosch", "model": "GBH 2-28"},
        ),
        dict(
            sku="MRO-RESP-3M-7503",
            name="Респиратор 3M 7503",
            full_name="Респиратор полумаска 3M 7503 силиконовая L",
            category="mro",
            unit="шт",
            gost="",
            typical_price_rub=3400,
            attributes={"brand": "3M", "size": "L"},
        ),
        dict(
            sku="MRO-CASKA-SOMZ",
            name="Каска защитная СОМЗ-55",
            full_name="Каска защитная СОМЗ-55 Hammer белая",
            category="mro",
            unit="шт",
            gost="ГОСТ EN 397-2012",
            typical_price_rub=890,
            attributes={"brand": "СОМЗ", "color": "white"},
        ),
        dict(
            sku="MRO-MASLO-SHELL-T46",
            name="Масло индустриальное Shell T46",
            full_name="Масло индустриальное Shell Tellus S2 M46 (208л)",
            category="mro",
            unit="бочка",
            gost="",
            typical_price_rub=78000,
            attributes={"brand": "Shell", "viscosity": "ISO VG 46"},
        ),
        dict(
            sku="MRO-VETOSH-50KG",
            name="Ветошь х/б, 50кг",
            full_name="Ветошь х/б белая обтирочная (тюк 50кг)",
            category="mro",
            unit="тюк",
            gost="",
            typical_price_rub=4200,
            attributes={"weight_kg": 50},
        ),
    ]
    return rows


def consumables() -> list[dict]:
    rows = []
    items = [
        ("Бумага А4 80г", 50, 350),
        ("Папка-регистратор 5см", 50, 220),
        ("Картридж HP CF283A", 8, 4800),
        ("Картридж Brother TN-2335", 8, 5300),
        ("Ручка шариковая синяя", 200, 35),
        ("Маркер перманентный чёрный", 200, 110),
        ("Степлер №24", 50, 480),
        ("Скрепки канцелярские 100шт", 200, 80),
        ("Скотч 50мм прозрачный", 80, 95),
        ("Скотч малярный 50мм", 80, 110),
    ]
    for i, (name, qty, price) in enumerate(items, start=1):
        rows.append(
            dict(
                sku=f"CONS-OFC-{i:03d}",
                name=name,
                full_name=name,
                category="consumables",
                unit="шт",
                gost="",
                typical_price_rub=price,
                attributes={"typical_qty_demand": qty},
            )
        )
    return rows


def chemistry() -> list[dict]:
    rows = [
        dict(
            sku="CHEM-PE-HDPE-273",
            name="Полиэтилен HDPE 273",
            full_name="Полиэтилен высокой плотности марка 273-83 ГОСТ 16338",
            category="chemistry",
            unit="т",
            gost="ГОСТ 16338-85",
            typical_price_rub=98000,
            attributes={"mfi": "5", "grade": "273"},
        ),
        dict(
            sku="CHEM-PE-LDPE-153",
            name="Полиэтилен LDPE 153",
            full_name="Полиэтилен низкой плотности марка 153 ГОСТ 16337",
            category="chemistry",
            unit="т",
            gost="ГОСТ 16337-77",
            typical_price_rub=92000,
            attributes={"mfi": "0.5", "grade": "153"},
        ),
        dict(
            sku="CHEM-PP-21030",
            name="Полипропилен 21030",
            full_name="Полипропилен гомополимер марка 21030 ГОСТ 26996",
            category="chemistry",
            unit="т",
            gost="ГОСТ 26996-86",
            typical_price_rub=112000,
            attributes={"grade": "21030"},
        ),
        dict(
            sku="CHEM-STAB-IRGAFOS-168",
            name="Стабилизатор Irgafos 168",
            full_name="Стабилизатор фосфитный Irgafos 168 (аналог)",
            category="chemistry",
            unit="кг",
            gost="",
            typical_price_rub=1300,
            attributes={"type": "phosphite_stabilizer"},
        ),
        dict(
            sku="CHEM-COLOR-CARBON-N220",
            name="Сажа техническая N220",
            full_name="Сажа техническая N220 (черный пигмент)",
            category="chemistry",
            unit="т",
            gost="ГОСТ 7885-86",
            typical_price_rub=130000,
            attributes={"grade": "N220"},
        ),
        dict(
            sku="CHEM-CAUSTIC-NAOH-CH",
            name="Сода каустическая NaOH",
            full_name="Натр едкий гранулированный ЧДА ГОСТ 4328",
            category="chemistry",
            unit="кг",
            gost="ГОСТ 4328-77",
            typical_price_rub=180,
            attributes={"purity": "ЧДА"},
        ),
        dict(
            sku="CHEM-ACID-H2SO4-92",
            name="Серная кислота 92%",
            full_name="Серная кислота техническая 92% ГОСТ 2184",
            category="chemistry",
            unit="т",
            gost="ГОСТ 2184-2013",
            typical_price_rub=28000,
            attributes={"purity": "техн"},
        ),
    ]
    return rows


def services() -> list[dict]:
    rows = [
        dict(
            sku="SVC-CLEAN-OFFICE-MONTH",
            name="Клининг офиса (помесячно)",
            full_name="Услуги клининга офиса 500м² 5 раз/нед месяц",
            category="services",
            unit="мес",
            gost="",
            typical_price_rub=85000,
            attributes={"area_sqm": 500},
        ),
        dict(
            sku="SVC-DELIVERY-AUTO",
            name="Доставка авто",
            full_name="Доставка автотранспортом 20т Москва-РФ (1 рейс)",
            category="services",
            unit="рейс",
            gost="",
            typical_price_rub=42000,
            attributes={"capacity_t": 20},
        ),
        dict(
            sku="SVC-TRAIN-WORKSHOP",
            name="Тренинг 1 день",
            full_name="Корпоративный тренинг 1 день (1 группа до 15 чел)",
            category="services",
            unit="день",
            gost="",
            typical_price_rub=68000,
            attributes={"max_attendees": 15},
        ),
    ]
    return rows


def main() -> None:
    all_rows: list[dict] = []
    all_rows += metals()
    all_rows += it_items()
    all_rows += mro_items()
    all_rows += consumables()
    all_rows += chemistry()
    all_rows += services()
    # Если меньше 200 — досыпаем синтетику mro/consumables-производных
    extra_idx = 1
    while len(all_rows) < 200:
        all_rows.append(
            dict(
                sku=f"MRO-EXTRA-{extra_idx:03d}",
                name=f"Расходник MRO позиция {extra_idx}",
                full_name=f"Расходный материал для технического обслуживания позиция {extra_idx}",
                category="mro",
                unit="шт",
                gost="",
                typical_price_rub=200 + extra_idx * 17,
                attributes={"synthetic": True},
            )
        )
        extra_idx += 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["sku", "name", "full_name", "category", "unit", "gost", "typical_price_rub", "attributes"]
        )
        for r in all_rows:
            w.writerow(
                [
                    r["sku"],
                    r["name"],
                    r["full_name"],
                    r["category"],
                    r["unit"],
                    r["gost"],
                    r["typical_price_rub"],
                    json.dumps(r["attributes"], ensure_ascii=False),
                ]
            )
    print(f"{len(all_rows)} NSI rows written to {OUT}")


if __name__ == "__main__":
    main()
