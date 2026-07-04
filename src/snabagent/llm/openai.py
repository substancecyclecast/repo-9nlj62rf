"""OpenAI клиент (DEV-only) с обязательным PII-маскированием."""
from __future__ import annotations

import time

import httpx

from ..settings import settings
from .base import LLMClient, LLMResponse
from .pii_masker import mask_pii, unmask_pii


class OpenAILLM(LLMClient):
    name = "openai"
    supports_json_mode = True
    supports_tools = True

    def __init__(self) -> None:
        if settings.app_env == "prod" and not settings.llm.enable_openai_in_prod:
            raise RuntimeError("OpenAI запрещён в prod (ENABLE_OPENAI_IN_PROD=false)")
        self._api_key = settings.llm.openai_api_key.get_secret_value()
        self._model = settings.llm.openai_model

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
            raise RuntimeError("OPENAI_API_KEY не задан")
        masked_system, mask_s = mask_pii(system)
        masked_user, mask_u = mask_pii(user)
        merged = {**mask_s, **mask_u}

        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=settings.llm.timeout_sec) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": masked_system},
                        {"role": "user", "content": masked_user},
                    ],
                    "temperature": temperature or settings.llm.temperature,
                    "max_tokens": max_tokens or 4000,
                    **(
                        {"response_format": {"type": "json_object"}} if json_schema else {}
                    ),
                },
            )
            resp.raise_for_status()
            data = resp.json()
        unmasked_text = unmask_pii(data["choices"][0]["message"]["content"], merged)
        return LLMResponse(
            text=unmasked_text,
            raw=data,
            model_name=self._model,
            prompt_tokens=data["usage"].get("prompt_tokens", 0),
            completion_tokens=data["usage"].get("completion_tokens", 0),
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
