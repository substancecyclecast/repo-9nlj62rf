"""Qwen Cloud (Alibaba DashScope) клиент — OpenAI-compatible, с PII-маскированием.

Провайдер для Qwen Cloud Global AI Hackathon. DashScope предоставляет
OpenAI-совместимый endpoint, поэтому запросы идут в формате `/chat/completions`.

Роль (`role`) определяет модель:
  * primary/fallback → `settings.llm.qwen_model`      (напр. qwen-max)
  * verifier         → `settings.llm.qwen_verifier_model` (напр. qwen-plus)

Разные модели для primary и verifier сохраняют анти-галлюцинационную гарантию,
даже когда оба провайдера — `qwen`.
"""

from __future__ import annotations

import time

import httpx

from ..settings import settings
from .base import LLMClient, LLMResponse
from .pii_masker import mask_pii, unmask_pii


class QwenLLM(LLMClient):
    name = "qwen"
    supports_json_mode = True
    supports_tools = True

    def __init__(self, role: str = "primary") -> None:
        if settings.app_env == "prod" and not settings.llm.enable_qwen_in_prod:
            raise RuntimeError("Qwen запрещён в prod (ENABLE_QWEN_IN_PROD=false)")
        self._api_key = settings.llm.qwen_api_key.get_secret_value()
        self._base_url = settings.llm.qwen_base_url.rstrip("/")
        # Верификатор использует отдельную модель Qwen (anti-hallucination).
        if role == "verifier":
            self._model = settings.llm.qwen_verifier_model
        else:
            self._model = settings.llm.qwen_model
        self._role = role

    async def complete(
        self,
        system: str,
        user: str,
        *,
        json_schema=None,
        tools=None,
        temperature=None,
        max_tokens=None,
        stop=None,
    ) -> LLMResponse:
        if not self._api_key:
            raise RuntimeError("QWEN_API_KEY (LLM_QWEN_API_KEY) не задан")

        masked_system, mask_s = mask_pii(system)
        masked_user, mask_u = mask_pii(user)
        merged = {**mask_s, **mask_u}

        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": masked_system},
                {"role": "user", "content": masked_user},
            ],
            "temperature": temperature if temperature is not None else settings.llm.temperature,
            "max_tokens": max_tokens or 4000,
        }
        if json_schema:
            payload["response_format"] = {"type": "json_object"}
        if tools:
            payload["tools"] = tools
        if stop:
            payload["stop"] = stop

        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=settings.llm.timeout_sec) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"].get("content") or ""
        unmasked_text = unmask_pii(content, merged)
        usage = data.get("usage") or {}
        return LLMResponse(
            text=unmasked_text,
            raw=data,
            model_name=self._model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
