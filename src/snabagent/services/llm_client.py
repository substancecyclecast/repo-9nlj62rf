"""LLM client wrapper with circuit breaker, retry, and timeout."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_LLM_TIMEOUT_SEC = 30
_CIRCUIT_FAILURE_THRESHOLD = 5
_CIRCUIT_WINDOW_SEC = 60
_CIRCUIT_OPEN_DURATION_SEC = 30


@dataclass
class CircuitBreaker:
    """Simple circuit breaker for LLM calls."""

    failure_threshold: int = _CIRCUIT_FAILURE_THRESHOLD
    window_sec: float = _CIRCUIT_WINDOW_SEC
    open_duration_sec: float = _CIRCUIT_OPEN_DURATION_SEC

    _failures: list[float] = field(default_factory=list)
    _opened_at: float | None = field(default=None, init=False)

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.time() - self._opened_at > self.open_duration_sec:
            self._opened_at = None
            self._failures.clear()
            logger.info("Circuit breaker: HALF-OPEN, allowing next call")
            return False
        return True

    def record_failure(self) -> None:
        now = time.time()
        self._failures = [t for t in self._failures if now - t < self.window_sec]
        self._failures.append(now)
        if len(self._failures) >= self.failure_threshold:
            self._opened_at = now
            logger.warning(
                "Circuit breaker: OPEN after %d failures in %ds",
                len(self._failures),
                self.window_sec,
            )

    def record_success(self) -> None:
        self._failures.clear()
        self._opened_at = None


# Global circuit breaker instance
circuit = CircuitBreaker()


class LLMUnavailableError(Exception):
    """Raised when the circuit breaker is open."""


async def call_llm_with_circuit_breaker(
    llm_func: Any,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Call an LLM function with circuit breaker protection.

    Args:
        llm_func: async callable that makes the LLM call
        *args, **kwargs: passed to llm_func

    Returns:
        LLM response

    Raises:
        LLMUnavailableError: if circuit is open
    """
    if circuit.is_open:
        raise LLMUnavailableError(
            "LLM circuit breaker is OPEN — fail-fast. "
            "Will retry automatically after cool-down."
        )

    try:
        result = await _retry_llm_call(llm_func, *args, **kwargs)
        circuit.record_success()
        return result
    except Exception:
        circuit.record_failure()
        raise


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _retry_llm_call(llm_func: Any, *args: Any, **kwargs: Any) -> Any:
    """Retry LLM call with exponential backoff (2 attempts max)."""
    import asyncio

    try:
        return await asyncio.wait_for(
            llm_func(*args, **kwargs),
            timeout=_LLM_TIMEOUT_SEC,
        )
    except TimeoutError:
        logger.warning("LLM call timed out after %ds", _LLM_TIMEOUT_SEC)
        raise
