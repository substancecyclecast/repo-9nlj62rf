"""YandexGPT клиент. SDK импортируется лениво, чтобы не ломать оффлайн-режим."""
from __future__ import annotations

import time

from ..settings import settings
from .base import LLMClient, LLMResponse


class YandexLLM(LLMClient):
    name = "yandex"
    supports_json_mode = True
    supports_tools = True

    def __init__(self) -> None:
        try:
            from yandex_cloud_ml_sdk import AsyncYCloudML  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "yandex-cloud-ml-sdk не установлен. pip install snabagent[prod]"
            ) from e
        self._sdk = AsyncYCloudML(
            folder_id=settings.llm.yc_folder_id,
            auth=settings.llm.yc_auth_token.get_secret_value(),
        )
        self._model_name = settings.llm.yc_llm_model
        self._model = self._sdk.models.completions(self._model_name)

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
        t0 = time.perf_counter()
        cfg = self._model.configure(
            temperature=temperature or settings.llm.temperature,
            max_tokens=max_tokens or 4000,
            response_format={"type": "json_object"} if json_schema else None,
        )
        messages = [
            {"role": "system", "text": system},
            {"role": "user", "text": user},
        ]
        result = await cfg.run(messages)
        latency = int((time.perf_counter() - t0) * 1000)
        usage = getattr(result, "usage", None)
        return LLMResponse(
            text=result.alternatives[0].text,
            raw=result.model_dump() if hasattr(result, "model_dump") else {},
            model_name=self._model_name,
            prompt_tokens=getattr(usage, "input_text_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            latency_ms=latency,
        )
