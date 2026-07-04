"""Абстрактный LLMClient и общая модель LLMResponse."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    text: str
    raw: dict[str, Any] = {}
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    confidence: float | None = None


class LLMClient(ABC):
    """Универсальный интерфейс LLM-провайдера."""

    name: str = "base"
    supports_json_mode: bool = False
    supports_tools: bool = False

    @abstractmethod
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
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        raise NotImplementedError("Embeddings обрабатываются через snabagent.vector.embeddings")
