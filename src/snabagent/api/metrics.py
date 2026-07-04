"""Prometheus-метрики SnabAgent.

Импортируем глобальные счётчики/гистограммы и регистрируем middleware.
"""
from __future__ import annotations

import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


def _safe_metric(constructor, name, *args, **kwargs):
    """Регистрирует метрику; если уже зарегистрирована (горячий перезапуск тестов) —
    возвращает существующую."""
    try:
        return constructor(name, *args, **kwargs)
    except ValueError:
        return REGISTRY._names_to_collectors.get(name)  # type: ignore[attr-defined]


REQUEST_COUNT = _safe_metric(
    Counter,
    "snabagent_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = _safe_metric(
    Histogram,
    "snabagent_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)
LOT_CREATED = _safe_metric(
    Counter,
    "snabagent_lots_created_total",
    "Lots created",
    ["customer_id"],
)
LOT_FINISHED = _safe_metric(
    Counter,
    "snabagent_lots_finished_total",
    "Lots finished with status",
    ["status"],
)
LOT_RUN_LATENCY = _safe_metric(
    Histogram,
    "snabagent_lot_run_duration_seconds",
    "End-to-end lot pipeline latency",
    buckets=(1, 5, 15, 30, 60, 120, 300, 600),
)
LLM_REQUESTS = _safe_metric(
    Counter,
    "snabagent_llm_requests_total",
    "LLM router requests",
    ["model", "status"],
)
LLM_LATENCY = _safe_metric(
    Histogram,
    "snabagent_llm_latency_seconds",
    "LLM latency",
    ["model"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)
ESCALATIONS = _safe_metric(
    Counter,
    "snabagent_escalations_total",
    "Escalations sent to n8n",
    ["reason", "severity"],
)
ACTIVE_WS = _safe_metric(
    Gauge,
    "snabagent_active_ws_connections",
    "Currently open WebSocket connections",
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Avoid label cardinality explosion: collapse /lots/{id} → /lots/{id}
        # FastAPI route matching available via request.scope["route"]
        route_path = path
        if request.scope.get("route") is not None and hasattr(request.scope["route"], "path"):
            route_path = request.scope["route"].path  # template form
        method = request.method
        start = time.time()
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            REQUEST_COUNT.labels(method=method, path=route_path, status="500").inc()
            raise
        finally:
            REQUEST_LATENCY.labels(method=method, path=route_path).observe(time.time() - start)
            try:
                REQUEST_COUNT.labels(
                    method=method, path=route_path, status=str(locals().get("status_code", "0"))
                ).inc()
            except Exception:
                pass


def metrics_endpoint() -> tuple[bytes, str]:
    """Возвращает payload + content-type для /metrics."""
    return generate_latest(), CONTENT_TYPE_LATEST
