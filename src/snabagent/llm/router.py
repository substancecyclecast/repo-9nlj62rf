"""LLM Router с fallback, retry, PII-masking и cost-метриками.

Поддерживаемые провайдеры: fake, yandex, gigachat, llama, openai.
"""
from __future__ import annotations

import logging
import time
from functools import lru_cache

from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from ..settings import settings
from .base import LLMClient, LLMResponse
from .fake import FakeLLM
from .pii_masker import mask_pii, unmask_pii

log = logging.getLogger(__name__)

# Approximate cost per 1K tokens (USD) for billing/monitoring
_COST_PER_1K: dict[str, dict[str, float]] = {
    "yandex": {"prompt": 0.0006, "completion": 0.0018},
    "gigachat": {"prompt": 0.0004, "completion": 0.0012},
    "llama": {"prompt": 0.0009, "completion": 0.0009},
    "openai": {"prompt": 0.01, "completion": 0.03},
    "fake": {"prompt": 0.0, "completion": 0.0},
}


def _record_llm_metric(model: str, status: str, duration_s: float) -> None:
    try:
        from ..api.metrics import LLM_LATENCY, LLM_REQUESTS

        LLM_REQUESTS.labels(model=model, status=status).inc()
        LLM_LATENCY.labels(model=model).observe(duration_s)
    except Exception:
        pass


def _estimate_cost(provider: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _COST_PER_1K.get(provider, _COST_PER_1K["fake"])
    return (prompt_tokens * rates["prompt"] + completion_tokens * rates["completion"]) / 1000


def _record_cost(provider: str, resp: LLMResponse) -> None:
    cost = _estimate_cost(provider, resp.prompt_tokens, resp.completion_tokens)
    try:
        from ..services.metering import usage_tracker

        usage_tracker.increment("_global_", metric="llm_total_tokens")
        usage_tracker.increment("_global_", metric="llm_cost_usd_x10000")
    except Exception:
        pass
    if cost > 0:
        log.debug(
            "LLM cost: provider=%s prompt_tok=%d compl_tok=%d est_cost=%.6f USD",
            provider,
            resp.prompt_tokens,
            resp.completion_tokens,
            cost,
        )


def _import_yandex():
    from .yandex import YandexLLM

    return YandexLLM


def _import_gigachat():
    from .gigachat import GigaChatLLM

    return GigaChatLLM


def _import_llama():
    from .llama import LlamaLLM

    return LlamaLLM


def _import_openai():
    from .openai import OpenAILLM

    return OpenAILLM


_REGISTRY = {
    "fake": lambda: FakeLLM,
    "yandex": _import_yandex,
    "gigachat": _import_gigachat,
    "llama": _import_llama,
    "openai": _import_openai,
}


@lru_cache(maxsize=8)
def get_llm(role: str = "primary") -> LLMClient:
    """role: primary | fallback | verifier | verifier_fallback — берём имя из settings.llm.<role>."""
    if role not in ("primary", "fallback", "verifier", "verifier_fallback"):
        raise ValueError(f"Unknown role: {role}")
    name = getattr(settings.llm, role)
    if name not in _REGISTRY:
        raise ValueError(f"Unknown LLM provider: {name}")
    cls = _REGISTRY[name]()
    return cls()


async def complete_with_fallback(
    system: str,
    user: str,
    *,
    role: str = "primary",
    mask_pii_enabled: bool = True,
    **kwargs,
) -> LLMResponse:
    """Пробуем primary с retry; при падении — fallback (role-aware).

    PII masking: по умолчанию user-промпт маскируется (ИНН, email, телефоны, ОГРН),
    а ответ демаскируется. Для FakeLLM маскировка пропускается.
    """
    primary = get_llm(role)

    # PII masking — только для реальных LLM
    pii_mapping: dict[str, str] = {}
    masked_user = user
    if mask_pii_enabled and primary.name != "fake":
        masked_user, pii_mapping = mask_pii(user)
        if pii_mapping:
            log.info("PII masked %d items before sending to %s", len(pii_mapping), primary.name)

    last_exc: Exception | None = None
    started = time.time()
    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(settings.llm.max_retries),
            wait=wait_exponential(min=1, max=10),
            reraise=True,
        ):
            with attempt:
                resp = await primary.complete(system, masked_user, **kwargs)
                _record_llm_metric(primary.name, "ok", time.time() - started)
                _record_cost(primary.name, resp)
                if pii_mapping:
                    resp = LLMResponse(
                        text=unmask_pii(resp.text, pii_mapping),
                        raw=resp.raw,
                        model_name=resp.model_name,
                        prompt_tokens=resp.prompt_tokens,
                        completion_tokens=resp.completion_tokens,
                        latency_ms=resp.latency_ms,
                        confidence=resp.confidence,
                    )
                return resp
    except Exception as e:
        last_exc = e
        _record_llm_metric(primary.name, "error", time.time() - started)

    # Role-aware fallback: для verifier берём verifier_fallback, чтобы не свалиться
    # на primary-модель (это сломает анти-галлюцинационный пайплайн).
    if role == "verifier":
        fallback_name = settings.llm.verifier_fallback
    else:
        fallback_name = settings.llm.fallback

    if fallback_name == primary.name:
        if last_exc:
            raise last_exc
        raise RuntimeError(f"primary ({primary.name}) failed and fallback is same provider")

    fallback_cls = _REGISTRY[fallback_name]()
    fallback = fallback_cls()
    fb_started = time.time()
    try:
        resp = await fallback.complete(system, masked_user, **kwargs)
        _record_llm_metric(fallback.name, "ok_fallback", time.time() - fb_started)
        _record_cost(fallback.name, resp)
        if pii_mapping:
            resp = LLMResponse(
                text=unmask_pii(resp.text, pii_mapping),
                raw=resp.raw,
                model_name=resp.model_name,
                prompt_tokens=resp.prompt_tokens,
                completion_tokens=resp.completion_tokens,
                latency_ms=resp.latency_ms,
                confidence=resp.confidence,
            )
        return resp
    except Exception:
        _record_llm_metric(fallback.name, "error_fallback", time.time() - fb_started)
        raise
