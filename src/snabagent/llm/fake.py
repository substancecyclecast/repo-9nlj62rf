"""Детерминированный FakeLLM для оффлайн-демо и тестов.

Распознаёт тип запроса по системному промпту/контексту и возвращает
заранее заготовленный JSON-ответ нужной формы. Никаких HTTP/токенов.
"""
from __future__ import annotations

import json
import random
import re
import time
from typing import Any

from .base import LLMClient, LLMResponse

# Маркеры в промптах для классификации
_PLANNER_MARKER = "ассистент отдела снабжения"
_SOURCER_RANK_MARKER = "ранкер поставщиков"
_COMMUNICATOR_RFQ_MARKER = "формирователь RFQ"
_OFFER_PARSER_MARKER = "парсер коммерческих предложений"
_NEGOTIATOR_MARKER = "переговорщик"
_VERIFIER_MARKER = "независимый аудитор"
_REPORTER_MARKER = "менеджер по снабжению"


class FakeLLM(LLMClient):
    name = "fake"
    supports_json_mode = True
    supports_tools = False

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    async def complete(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict | None = None,
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        t0 = time.perf_counter()
        text = self._dispatch(system, user)
        latency = int((time.perf_counter() - t0) * 1000)
        return LLMResponse(
            text=text,
            raw={"fake": True, "system_preview": system[:80], "user_preview": user[:120]},
            model_name="fake-llm/deterministic-v1",
            prompt_tokens=max(1, len(system) // 4 + len(user) // 4),
            completion_tokens=max(1, len(text) // 4),
            latency_ms=latency,
        )

    # ------------------------------------------------------------------
    def _dispatch(self, system: str, user: str) -> str:
        joined = system + "\n" + user
        if _PLANNER_MARKER in joined:
            return self._planner(user)
        if _SOURCER_RANK_MARKER in joined:
            return self._sourcer(user)
        if _OFFER_PARSER_MARKER in joined or "извлеки структурированное КП" in joined:
            return self._offer(user)
        if _COMMUNICATOR_RFQ_MARKER in joined:
            return self._communicator_rfq(user)
        if _NEGOTIATOR_MARKER in joined:
            return self._negotiator(user)
        if _VERIFIER_MARKER in joined:
            return self._verifier(user)
        if _REPORTER_MARKER in joined:
            return self._reporter(user)
        # Универсальный fallback
        return json.dumps({"status": "ok", "fake": True})

    # ---- Planner ------------------------------------------------------
    def _planner(self, user: str) -> str:
        """Извлекаем кандидаты из user-prompt и строим валидный JSON-ответ."""
        items: list[dict[str, Any]] = []
        # Парсим блоки «Фраза:» c кандидатами (см. planner_user.j2)
        phrase_blocks = re.findall(
            r'Фраза:\s*"([^"]+)"\s*Кандидаты:(.*?)(?=Фраза:|$)',
            user,
            flags=re.DOTALL,
        )
        for phrase, block in phrase_blocks:
            cands = re.findall(
                r"-\s*sku=([\w\-]+)\s*\|\s*name=\"([^\"]+)\"\s*\|\s*category=(\w+)\s*\|\s*unit=([^\s|]+)\s*\|"
                r"\s*gost=([^|]+?)\s*\|\s*typical_price=([^|]+?)\s*\|\s*similarity=([\d.]+)",
                block,
            )
            # cands tuples = (sku, name, category, unit, gost, typical_price, similarity)
            if not cands:
                continue
            top = cands[0]
            qty = _extract_qty(phrase)
            # Confidence на основе рангового разрыва top-1 vs top-2 + базы 0.75.
            # Реальные эмбеддинги дают высокий cosine; bag-of-trigrams даёт низкий, но
            # сам факт top-1 в семантическом поиске — уже сильный сигнал.
            top1_sim = float(top[6])
            top2_sim = float(cands[1][6]) if len(cands) > 1 else 0.0
            margin = (top1_sim - top2_sim) / (top1_sim + 1e-6) if top1_sim > 0 else 0
            confidence = min(0.98, max(0.5, 0.75 + 0.20 * margin + 0.05 * top1_sim))
            try:
                typical_price = float(top[5].strip())
            except ValueError:
                typical_price = None
            items.append(
                {
                    "raw_phrase": phrase,
                    "matched_nsi_sku": top[0],
                    "matched_nsi_name": top[1],
                    "qty": qty,
                    "unit": top[3].strip(),
                    "typical_price_rub": typical_price,
                    "gost": top[4].strip(),
                    "lead_time_days": _extract_days(phrase),
                    "preferred_supplier_hint": _extract_supplier_hint(phrase),
                    "confidence": round(confidence, 3),
                    "alternatives": [
                        {"sku": c[0], "name": c[1], "score": float(c[6])}
                        for c in cands[1:4]
                    ],
                }
            )
        category = _infer_category(items) or "mro"
        overall = (
            sum(i["confidence"] for i in items) / len(items) if items else 0.0
        )
        out = {
            "items": items,
            "category": category,
            "overall_confidence": round(overall, 3),
            "escalation_needed": overall < 0.65 or not items,
            "escalation_reason": (
                None if overall >= 0.65 and items else "Низкая уверенность маппинга НСИ"
            ),
        }
        return json.dumps(out, ensure_ascii=False)

    # ---- Sourcer ranker ----------------------------------------------
    def _sourcer(self, user: str) -> str:
        """Простое ранжирование: берём первые N кандидатов и присваиваем score 0.95→0.60."""
        # Формат входа задаётся в sourcer_user.j2: список JSON-кандидатов
        try:
            payload = json.loads(_extract_json_block(user))
            cands = payload.get("candidates", [])
        except Exception:
            cands = []
        ranked = []
        for i, c in enumerate(cands[:10]):
            ranked.append(
                {
                    "supplier_id": c.get("supplier_id") or c.get("inn"),
                    "inn": c.get("inn"),
                    "name": c.get("name"),
                    "contact_email": c.get("contact_email"),
                    "source": c.get("source", "historical"),
                    "rank": i + 1,
                    "score": round(max(0.6, 0.95 - i * 0.04), 2),
                    "reasoning": c.get("reasoning")
                    or f"Источник {c.get('source')}; historical_score={c.get('historical_score', 0.7)}",
                }
            )
        return json.dumps({"suppliers": ranked}, ensure_ascii=False)

    # ---- Communicator RFQ generator ---------------------------------
    def _communicator_rfq(self, user: str) -> str:
        """RFQ-генератор детерминированно возвращает пустой stub — основной шаблон рендерится Jinja-ом."""
        return json.dumps({"subject_suffix": "Запрос КП", "tone_ok": True})

    # ---- Offer parser ------------------------------------------------
    def _offer(self, user: str) -> str:
        """Извлекаем числа из «текста КП» эвристически — для демо."""
        # Очень простая эвристика: берём первое число с «руб» как цену, первое число со словом «дн» — как срок.
        price_match = re.search(r"(\d[\d\s]{2,15})\s*(?:руб|RUB|₽)", user, flags=re.IGNORECASE)
        lt_match = re.search(r"(\d{1,3})\s*(?:дн|day)", user, flags=re.IGNORECASE)
        total = int(re.sub(r"\s+", "", price_match.group(1))) if price_match else 1_000_000
        lead_time = int(lt_match.group(1)) if lt_match else 30
        offer = {
            "currency": "RUB",
            "vat_included": True,
            "total_price": total,
            "lead_time_days": lead_time,
            "delivery_terms": "EXW склад поставщика",
            "payment_terms": "30 банковских дней по факту",
            "validity_days": 14,
            "items": [
                {
                    "name": "Позиция (см. ТЗ)",
                    "matched_sku": None,
                    "qty": 1,
                    "unit": "ед",
                    "unit_price": total,
                    "subtotal": total,
                }
            ],
            "discrepancies_with_spec": [],
        }
        return json.dumps(offer, ensure_ascii=False)

    # ---- Negotiator --------------------------------------------------
    def _negotiator(self, user: str) -> str:
        return json.dumps(
            {
                "tone_ok": True,
                "suggested_target_discount_pct": 5.0,
                "rationale": "Снижение в пределах разумного отклонения от средне-рыночной цены.",
            },
            ensure_ascii=False,
        )

    # ---- Verifier ----------------------------------------------------
    def _verifier(self, user: str) -> str:
        """Парсим offer/spec из user; ищем явные несоответствия (срок, gost)."""
        offered_lt = _find_number(user, r"в КП\s*—\s*(\d+)")
        requested_lt = _find_number(user, r"запрошено\s+(\d+)\s+дней")
        discrepancies: list[dict[str, Any]] = []
        if requested_lt is not None and offered_lt is not None and offered_lt > requested_lt:
            discrepancies.append(
                {
                    "type": "lead_time_exceeded",
                    "severity": "high",
                    "message": f"Срок поставки {offered_lt} > запрошенных {requested_lt}",
                    "evidence": "Из секции 'Сроки' в исходных данных проверки.",
                }
            )
        # Проверка ИНН через флаг SPARK
        if "spark_data_json" in user and '"active": false' in user.lower():
            discrepancies.append(
                {
                    "type": "spark_not_found",
                    "severity": "high",
                    "message": "ИНН отсутствует в реестре СПАРК-mock",
                    "evidence": "spark_data.active=false",
                }
            )
        high = sum(1 for d in discrepancies if d["severity"] == "high")
        medium = sum(1 for d in discrepancies if d["severity"] == "medium")
        confidence = max(0.0, 1 - 0.3 * high - 0.1 * medium)
        rec = "approve" if confidence >= 0.7 else ("reject" if confidence < 0.4 else "escalate_to_human")
        return json.dumps(
            {
                "discrepancies": discrepancies,
                "confidence_score": round(confidence, 2),
                "recommendation": rec,
            },
            ensure_ascii=False,
        )

    # ---- Reporter ---------------------------------------------------
    def _reporter(self, user: str) -> str:
        top1 = re.search(r"Top-1:\s*([^(]+)\(([^\)]+)\)", user)
        savings = re.search(r"Экономия[^\d]*([\d.]+)%", user)
        sup = top1.group(1).strip() if top1 else "поставщик A"
        details = top1.group(2).strip() if top1 else "—"
        sav = savings.group(1) if savings else "0"
        return (
            f"Рекомендуется выбрать {sup} (условия: {details}). "
            f"Экономия vs средне-рыночной цены — {sav}%. "
            f"Кандидат прошёл независимую верификацию: сроки, ГОСТ и реквизиты совпадают со спецификацией. "
            f"Финальный выбор остаётся за снабженцем."
        )


# ============= helpers =============================================
_QTY_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:т|тонн|шт|кг|м|упак|рулон)?", flags=re.IGNORECASE)
_DAYS_RE = re.compile(r"(\d+)\s*(?:дн|day)", flags=re.IGNORECASE)


def _extract_qty(phrase: str) -> float:
    m = _QTY_RE.search(phrase)
    if not m:
        return 1.0
    return float(m.group(1).replace(",", "."))


def _extract_days(phrase: str) -> int | None:
    m = _DAYS_RE.search(phrase)
    return int(m.group(1)) if m else None


def _extract_supplier_hint(phrase: str) -> str | None:
    m = re.search(r"(?:у|от)\s+([A-Za-zА-ЯЁа-яё][\w\-]+)", phrase)
    return m.group(1) if m else None


def _infer_category(items: list[dict]) -> str | None:
    if not items:
        return None
    skus = [i.get("matched_nsi_sku") or "" for i in items]
    if any(s.startswith("MET-") for s in skus):
        return "metals"
    if any(s.startswith("IT-") for s in skus):
        return "it"
    if any(s.startswith("CHEM-") for s in skus):
        return "chemistry"
    if any(s.startswith("MRO-") for s in skus):
        return "mro"
    if any(s.startswith("CONS-") for s in skus):
        return "consumables"
    return "services"


def _find_number(text: str, pattern: str) -> int | None:
    m = re.search(pattern, text, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


def _extract_json_block(text: str) -> str:
    """Балансированный поиск первого верхнеуровневого JSON-объекта.

    Перебирает символы от первого '{', считая глубину фигурных скобок,
    игнорирует фигурные скобки внутри строк. Возвращает подстроку первого
    сбалансированного блока или '{}'.
    """
    start = text.find("{")
    if start == -1:
        return "{}"
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]
