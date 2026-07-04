"""GigaChat 2 Pro клиент. SDK импортируется лениво."""
from __future__ import annotations

import asyncio
import time

from ..settings import settings
from .base import LLMClient, LLMResponse


class GigaChatLLM(LLMClient):
    name = "gigachat"
    supports_json_mode = True
    supports_tools = True

    def __init__(self) -> None:
        try:
            from gigachat import GigaChat  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("gigachat SDK не установлен. pip install snabagent[prod]") from e
        self._client = GigaChat(
            credentials=settings.llm.gigachat_auth_key.get_secret_value(),
            scope=settings.llm.gigachat_scope,
            model=settings.llm.gigachat_model,
            verify_ssl_certs=settings.llm.gigachat_verify_ssl,
        )

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
        from gigachat.models import Chat, Messages, MessagesRole  # type: ignore

        loop = asyncio.get_event_loop()

        def _sync():
            t0 = time.perf_counter()
            payload = Chat(
                messages=[
                    Messages(role=MessagesRole.SYSTEM, content=system),
                    Messages(role=MessagesRole.USER, content=user),
                ],
                temperature=temperature or settings.llm.temperature,
                max_tokens=max_tokens or 4000,
            )
            resp = self._client.chat(payload)
            return resp, time.perf_counter() - t0

        resp, dt = await loop.run_in_executor(None, _sync)
        return LLMResponse(
            text=resp.choices[0].message.content,
            raw=resp.dict() if hasattr(resp, "dict") else {},
            model_name=settings.llm.gigachat_model,
            prompt_tokens=getattr(resp.usage, "prompt_tokens", 0),
            completion_tokens=getattr(resp.usage, "completion_tokens", 0),
            latency_ms=int(dt * 1000),
        )
