"""License metering: track API usage + LLM cost per tenant for billing."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Plan limits (lots per month)
PLAN_LIMITS = {
    "pilot": 100,
    "pro": 1000,
    "enterprise": None,  # unlimited
}

# LLM cost per 1K tokens (USD). Keep in sync with llm/router._COST_PER_1K
LLM_COST_PER_1K: dict[str, dict[str, float]] = {
    "yandex": {"prompt": 0.0006, "completion": 0.0018},
    "gigachat": {"prompt": 0.0004, "completion": 0.0012},
    "llama": {"prompt": 0.0009, "completion": 0.0009},
    "openai": {"prompt": 0.01, "completion": 0.03},
    "fake": {"prompt": 0.0, "completion": 0.0},
}


class UsageTracker:
    """In-memory usage tracker. In production, back by Redis or DB for persistence."""

    def __init__(self) -> None:
        self._counters: dict[str, dict[str, int]] = {}
        self._cost_accum: dict[str, float] = {}

    def _key(self, tenant_id: str) -> str:
        return f"{tenant_id}:{datetime.now(UTC).strftime('%Y-%m')}"

    def increment(self, tenant_id: str, metric: str = "lots_processed") -> int:
        """Increment usage counter. Returns new total."""
        key = self._key(tenant_id)
        if key not in self._counters:
            self._counters[key] = {}
        self._counters[key][metric] = self._counters[key].get(metric, 0) + 1
        return self._counters[key][metric]

    def record_llm_cost(
        self,
        tenant_id: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Record LLM call cost. Returns estimated cost in USD."""
        rates = LLM_COST_PER_1K.get(provider, LLM_COST_PER_1K["fake"])
        cost = (prompt_tokens * rates["prompt"] + completion_tokens * rates["completion"]) / 1000
        key = self._key(tenant_id)
        self._cost_accum[key] = self._cost_accum.get(key, 0.0) + cost
        self.increment(tenant_id, metric="llm_calls")
        self.increment(tenant_id, metric="llm_total_tokens")
        return cost

    def get_llm_cost(self, tenant_id: str) -> float:
        """Get accumulated LLM cost for current month (USD)."""
        key = self._key(tenant_id)
        return self._cost_accum.get(key, 0.0)

    def get_usage(self, tenant_id: str) -> dict[str, int]:
        """Get current month's usage for a tenant."""
        key = self._key(tenant_id)
        return dict(self._counters.get(key, {}))

    def get_usage_report(self, tenant_id: str, plan: str = "pilot") -> dict[str, Any]:
        """Full usage report including LLM costs."""
        usage = self.get_usage(tenant_id)
        limit_info = self.check_limit(tenant_id, plan)
        return {
            **limit_info,
            "llm_calls": usage.get("llm_calls", 0),
            "llm_total_tokens": usage.get("llm_total_tokens", 0),
            "llm_cost_usd": round(self.get_llm_cost(tenant_id), 4),
        }

    def check_limit(self, tenant_id: str, plan: str = "pilot") -> dict[str, Any]:
        """Check if tenant is within plan limits."""
        usage = self.get_usage(tenant_id)
        lots = usage.get("lots_processed", 0)
        limit = PLAN_LIMITS.get(plan)

        result: dict[str, Any] = {
            "tenant_id": tenant_id,
            "plan": plan,
            "lots_processed": lots,
            "limit": limit,
            "within_limit": True,
        }

        if limit is not None and lots >= limit:
            result["within_limit"] = False
            logger.warning(
                "Tenant %s exceeded %s plan limit: %d/%d lots",
                tenant_id,
                plan,
                lots,
                limit,
            )

        return result


# Global tracker instance
usage_tracker = UsageTracker()
