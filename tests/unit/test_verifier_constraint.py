"""Verifier должен отличаться от primary в реальном (не-fake) режиме."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from snabagent.settings import LLMSettings


def test_verifier_must_differ_from_primary_in_real_mode() -> None:
    with pytest.raises(ValidationError):
        LLMSettings(primary="yandex", verifier="yandex")


def test_fake_primary_allows_fake_verifier() -> None:
    """В offline-demo режиме совпадение разрешено."""
    s = LLMSettings(primary="fake", verifier="fake")
    assert s.verifier == "fake"


def test_different_real_models_allowed() -> None:
    s = LLMSettings(primary="yandex", verifier="gigachat")
    assert s.primary != s.verifier


def test_verifier_fallback_default() -> None:
    s = LLMSettings()
    assert s.verifier_fallback == "fake"
