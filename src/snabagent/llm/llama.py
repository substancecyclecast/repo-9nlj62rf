"""Llama 3.3 70B через OpenAI-совместимый API (Together / vLLM / RunPod)."""
from __future__ import annotations

import time

import httpx

from ..settings import settings
from .base import LLMClient, LLMResponse


class LlamaLLM(LLMClient):
    name = "llama"
    supports_json_mode = True
    supports_tools = False

    def __init__(self) -> None:
        self._base_url = settings.llm.llama_base_url.rstrip("/")
        self._api_key = settings.llm.llama_api_key.get_secret_value()
        self._model = settings.llm.llama_model

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
        if not self._base_url or not self._api_key:
            raise RuntimeError("LLAMA_BASE_URL/LLAMA_API_KEY не настроены")
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=settings.llm.timeout_sec) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature or settings.llm.temperature,
                    "max_tokens": max_tokens or 4000,
                    **(
                        {"response_format": {"type": "json_object"}} if json_schema else {}
                    ),
                    "stop": stop,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            raw=data,
            model_name=self._model,
            prompt_tokens=data["usage"].get("prompt_tokens", 0),
            completion_tokens=data["usage"].get("completion_tokens", 0),
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )
