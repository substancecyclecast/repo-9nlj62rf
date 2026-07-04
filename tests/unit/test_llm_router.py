"""Tests for LLM router module."""
from __future__ import annotations

from snabagent.llm.base import LLMClient
from snabagent.llm.router import _record_llm_metric, get_llm


def test_get_llm_default():
    llm = get_llm()
    assert isinstance(llm, LLMClient)


def test_get_llm_primary():
    llm = get_llm("primary")
    assert isinstance(llm, LLMClient)


def test_get_llm_verifier():
    llm = get_llm("verifier")
    assert isinstance(llm, LLMClient)


def test_record_llm_metric():
    _record_llm_metric("test-model", "ok", 1.0)
