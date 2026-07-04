"""Регуляторный фильтр 223-ФЗ для негоциаций."""
from __future__ import annotations

from dataclasses import dataclass

from ...settings import settings


@dataclass
class AllowResult:
    allowed: bool
    reason: str


def check(lot: dict) -> AllowResult:
    if lot.get("phase") == "post_tender_published":
        return AllowResult(False, "Лот опубликован на ЭТП — авто-коммуникации запрещены 223-ФЗ")
    if (lot.get("category") or "") not in settings.regulatory_allowed_categories:
        return AllowResult(
            False, f"Категория '{lot.get('category')}' вне whitelist для авто-торга"
        )
    max_amount = settings.regulatory_max_unregulated_amount_rub
    if lot.get("phase") == "unregulated" and (lot.get("total_estimated_rub") or 0) > max_amount:
        return AllowResult(
            False,
            f"Сумма {lot.get('total_estimated_rub')} > порога {settings.regulatory_max_unregulated_amount_rub}",
        )
    return AllowResult(True, "ok")
