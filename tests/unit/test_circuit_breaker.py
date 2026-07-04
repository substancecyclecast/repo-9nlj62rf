"""Tests for circuit breaker in LLM client."""
from __future__ import annotations

import time

from snabagent.services.llm_client import CircuitBreaker


def test_circuit_closed_by_default():
    cb = CircuitBreaker()
    assert cb.is_open is False


def test_circuit_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3, window_sec=60)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open is False
    cb.record_failure()
    assert cb.is_open is True


def test_circuit_resets_on_success():
    cb = CircuitBreaker(failure_threshold=2, window_sec=60)
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    assert cb.is_open is False


def test_circuit_half_open_after_duration():
    cb = CircuitBreaker(failure_threshold=1, window_sec=60, open_duration_sec=0.1)
    cb.record_failure()
    assert cb.is_open is True
    time.sleep(0.15)
    assert cb.is_open is False


def test_circuit_clears_old_failures():
    cb = CircuitBreaker(failure_threshold=3, window_sec=0.1)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.15)
    cb.record_failure()
    assert cb.is_open is False
