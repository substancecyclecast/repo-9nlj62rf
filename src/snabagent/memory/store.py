"""Персистентная память: профиль компании, надёжность поставщиков, прошлые решения.

Память живёт в SQL (CompanyProfile / SupplierMemory / LotDecisionMemory) и, в
отличие от эпизодического состояния лота, накапливается между запусками —
это и есть MemoryAgent-грань SnabAgent:

* recall()    — подтягивает контекст ДО начала пайплайна (узел memory_recall);
* writeback() — обновляет скоры надёжности и записывает решение ПОСЛЕ отчёта
                (узел memory_writeback), делая агента самообучающимся.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from ..db.models import CompanyProfile, LotDecisionMemory, SupplierMemory
from ..db.session import AsyncSessionLocal

log = logging.getLogger(__name__)

_MAX_PAST_LOTS = 5


async def get_or_create_profile(customer_id: str) -> dict:
    """Возвращает профиль предпочтений компании (создаёт дефолтный при отсутствии)."""
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(select(CompanyProfile).where(CompanyProfile.customer_id == customer_id))
        ).scalar_one_or_none()
        if row is None:
            row = CompanyProfile(customer_id=customer_id)
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return {
            "weight_price": row.weight_price,
            "weight_lead_time": row.weight_lead_time,
            "weight_quality": row.weight_quality,
            "preferred_regions": list(row.preferred_regions or []),
            "blacklisted_inns": list(row.blacklisted_inns or []),
            "notes": row.notes,
            "lots_processed": row.lots_processed,
        }


async def recall(customer_id: str, category: str | None) -> dict:
    """Собирает память для лота: профиль, надёжность поставщиков, похожие прошлые лоты."""
    if not customer_id:
        return {"profile": {}, "supplier_memory": {}, "past_lots": []}

    profile = await get_or_create_profile(customer_id)

    async with AsyncSessionLocal() as session:
        sm_rows = (await session.execute(select(SupplierMemory).where(SupplierMemory.customer_id == customer_id))).scalars().all()
        supplier_memory = {
            r.inn: {
                "supplier_name": r.supplier_name,
                "reliability_score": r.reliability_score,
                "times_seen": r.times_seen,
                "times_selected": r.times_selected,
                "on_time_count": r.on_time_count,
                "avg_quality": r.avg_quality,
                "last_price_rub": float(r.last_price_rub) if r.last_price_rub is not None else None,
            }
            for r in sm_rows
            if r.inn
        }

        q = (
            select(LotDecisionMemory)
            .where(LotDecisionMemory.customer_id == customer_id)
            .order_by(LotDecisionMemory.created_at.desc())
            .limit(_MAX_PAST_LOTS)
        )
        if category:
            q = q.where(LotDecisionMemory.category == category)
        past_rows = (await session.execute(q)).scalars().all()
        past_lots = [
            {
                "category": r.category,
                "chosen_supplier_name": r.chosen_supplier_name,
                "chosen_supplier_inn": r.chosen_supplier_inn,
                "total_rub": float(r.total_rub) if r.total_rub is not None else None,
                "savings_pct": r.savings_pct,
                "summary": r.summary,
            }
            for r in past_rows
        ]

    return {
        "profile": profile,
        "supplier_memory": supplier_memory,
        "past_lots": past_lots,
    }


def apply_reliability_boost(candidates: list[dict], supplier_memory: dict) -> list[dict]:
    """Обогащает кандидатов накопленным скором надёжности из памяти.

    Не переупорядочивает жёстко — добавляет поля `memory_reliability` /
    `memory_times_selected`, которые LLM-ранкер Sourcer учитывает при ранжировании.
    """
    if not supplier_memory:
        return candidates
    for c in candidates:
        mem = supplier_memory.get(c.get("inn"))
        if mem:
            c["memory_reliability"] = round(mem.get("reliability_score", 0.5), 3)
            c["memory_times_selected"] = mem.get("times_selected", 0)
            c["memory_seen_before"] = True
    return candidates


def summarize_for_prompt(memory: dict, max_suppliers: int = 5) -> str:
    """Компактное текстовое резюме памяти для вставки в промпты агентов."""
    if not memory:
        return "Память пуста (первое обращение этой компании)."
    profile = memory.get("profile") or {}
    lines = []
    if profile:
        lines.append(
            "Предпочтения компании: "
            f"цена={profile.get('weight_price')}, "
            f"срок={profile.get('weight_lead_time')}, "
            f"качество={profile.get('weight_quality')}."
        )
    sm = memory.get("supplier_memory") or {}
    if sm:
        top = sorted(sm.items(), key=lambda kv: kv[1].get("reliability_score", 0), reverse=True)[:max_suppliers]
        rel = "; ".join(
            f"{v.get('supplier_name') or inn} (надёжность {v.get('reliability_score'):.2f}, "
            f"выбран {v.get('times_selected', 0)}x)"
            for inn, v in top
        )
        lines.append(f"Известные поставщики: {rel}.")
    past = memory.get("past_lots") or []
    if past:
        lines.append(f"Похожих прошлых лотов в памяти: {len(past)}.")
    return " ".join(lines) if lines else "Память пуста."


async def writeback(
    customer_id: str,
    *,
    category: str | None,
    report: dict | None,
    verifications: list[dict] | None,
    lot_id: str | None = None,
) -> None:
    """Обновляет память после завершения лота (самообучение агента).

    * повышает reliability_score выбранного поставщика (EMA);
    * инкрементирует times_seen для всех проверенных;
    * пишет запись о решении в LotDecisionMemory;
    * увеличивает счётчик обработанных лотов у профиля.
    """
    if not customer_id:
        return
    report = report or {}
    verifications = verifications or []
    top_3 = report.get("top_3") or []
    winner = top_3[0] if top_3 else None

    winner_inn = None
    winner_name = None
    winner_total = None
    if winner:
        winner_inn = winner.get("inn") or winner.get("supplier_inn")
        winner_name = winner.get("supplier_name") or winner.get("name")
        winner_total = winner.get("total_price") or winner.get("total_rub")

    try:
        async with AsyncSessionLocal() as session:
            for v in verifications:
                inn = v.get("inn") or v.get("supplier_inn")
                if not inn:
                    continue
                row = (
                    await session.execute(
                        select(SupplierMemory).where(
                            SupplierMemory.customer_id == customer_id,
                            SupplierMemory.inn == inn,
                        )
                    )
                ).scalar_one_or_none()
                if row is None:
                    row = SupplierMemory(
                        customer_id=customer_id,
                        inn=inn,
                        supplier_name=v.get("supplier_name"),
                    )
                    session.add(row)
                row.times_seen = (row.times_seen or 0) + 1
                row.last_category = category
                conf = float(v.get("confidence_score") or 0.5)
                is_winner = inn == winner_inn
                # EMA скора надёжности: сигнал = уверенность верификатора (+бонус победителю)
                signal = min(1.0, conf + (0.1 if is_winner else 0.0))
                row.reliability_score = round(0.7 * (row.reliability_score or 0.5) + 0.3 * signal, 4)
                if v.get("lead_time_meets_spec"):
                    row.on_time_count = (row.on_time_count or 0) + 1
                if is_winner:
                    row.times_selected = (row.times_selected or 0) + 1
                    if winner_total is not None:
                        try:
                            row.last_price_rub = float(winner_total)
                        except (TypeError, ValueError):
                            pass

            session.add(
                LotDecisionMemory(
                    customer_id=customer_id,
                    lot_id=lot_id,
                    category=category,
                    chosen_supplier_inn=winner_inn,
                    chosen_supplier_name=winner_name,
                    total_rub=_safe_float(winner_total),
                    savings_pct=_safe_float(report.get("savings_vs_avg_pct")),
                    summary=(report.get("summary") or "")[:1000] or None,
                )
            )

            profile = (
                await session.execute(select(CompanyProfile).where(CompanyProfile.customer_id == customer_id))
            ).scalar_one_or_none()
            if profile is None:
                profile = CompanyProfile(customer_id=customer_id)
                session.add(profile)
            profile.lots_processed = (profile.lots_processed or 0) + 1

            await session.commit()
    except Exception as e:  # noqa: BLE001 — память не должна ронять пайплайн
        log.warning("memory writeback failed: %s", e)


def _safe_float(v) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
