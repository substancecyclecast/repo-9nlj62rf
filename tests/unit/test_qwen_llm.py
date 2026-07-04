"""Тесты Qwen-провайдера: настройки, выбор модели по роли, OpenAI-совместимый вызов."""

from __future__ import annotations

import httpx
import pytest

from snabagent.llm.qwen import QwenLLM
from snabagent.llm.router import _REGISTRY, get_llm
from snabagent.settings import LLMSettings


def test_qwen_registered_in_router() -> None:
    assert "qwen" in _REGISTRY


def test_qwen_same_provider_ok_if_models_differ() -> None:
    s = LLMSettings(
        primary="qwen",
        verifier="qwen",
        qwen_model="qwen-max",
        qwen_verifier_model="qwen-plus",
    )
    assert s.primary == "qwen" and s.verifier == "qwen"


def test_qwen_same_model_forbidden() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        LLMSettings(
            primary="qwen",
            verifier="qwen",
            qwen_model="qwen-max",
            qwen_verifier_model="qwen-max",
        )


def test_qwen_role_selects_model(monkeypatch) -> None:
    from snabagent import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings.llm, "qwen_model", "qwen-max")
    monkeypatch.setattr(settings_mod.settings.llm, "qwen_verifier_model", "qwen-plus")
    monkeypatch.setattr(settings_mod.settings.llm, "qwen_api_key", settings_mod.SecretStr("k"))
    assert QwenLLM(role="primary")._model == "qwen-max"
    assert QwenLLM(role="verifier")._model == "qwen-plus"


def test_get_llm_qwen_verifier_is_role_aware(monkeypatch) -> None:
    from snabagent import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings.llm, "primary", "qwen")
    monkeypatch.setattr(settings_mod.settings.llm, "verifier", "qwen")
    monkeypatch.setattr(settings_mod.settings.llm, "qwen_model", "qwen-max")
    monkeypatch.setattr(settings_mod.settings.llm, "qwen_verifier_model", "qwen-plus")
    monkeypatch.setattr(settings_mod.settings.llm, "qwen_api_key", settings_mod.SecretStr("k"))
    get_llm.cache_clear()
    assert get_llm("primary")._model == "qwen-max"
    assert get_llm("verifier")._model == "qwen-plus"
    get_llm.cache_clear()


@pytest.mark.asyncio
async def test_qwen_complete_openai_compatible(monkeypatch) -> None:
    """Проверяем, что запрос идёт на compatible-mode endpoint и ответ парсится."""
    from snabagent import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings.llm, "qwen_api_key", settings_mod.SecretStr("test-key"))
    captured: dict = {}

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": '{"ok": true}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8},
            }

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _Client)

    llm = QwenLLM(role="primary")
    resp = await llm.complete("system", "user", json_schema={"type": "object"})

    assert "compatible-mode/v1/chat/completions" in captured["url"]
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert resp.text == '{"ok": true}'
    assert resp.prompt_tokens == 12
    assert resp.completion_tokens == 8
    assert resp.model_name == "qwen-max"
