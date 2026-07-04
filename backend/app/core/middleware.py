"""HTTP middleware: request context/metrics and in-memory rate limiting."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.metrics import metrics


def _route_template(request: Request) -> str:
    """Stable, low-cardinality label for a request path.

    Numeric path segments (org ids, batch ids, …) are collapsed to ``:id`` so the
    metrics registry doesn't explode with one series per organization.
    """
    parts = []
    for seg in request.url.path.split("/"):
        parts.append(":id" if seg.isdigit() else seg)
    return "/".join(parts) or "/"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, time the request, and record metrics."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        start = time.perf_counter()
        route = _route_template(request)
        metrics.inc("mandate_http_requests_in_flight_total", method=request.method)
        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - start
            metrics.inc("mandate_http_requests_total", method=request.method, route=route, status="500")
            metrics.observe("mandate_http_request_duration_seconds", duration, route=route)
            raise
        duration = time.perf_counter() - start
        metrics.inc(
            "mandate_http_requests_total",
            method=request.method,
            route=route,
            status=str(response.status_code),
        )
        metrics.observe("mandate_http_request_duration_seconds", duration, route=route)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{duration * 1000:.1f}"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window-ish sliding token check per client IP.

    Disabled by default (sandbox/demo). Enable with ``MANDATE_RATE_LIMIT_ENABLED=true``.
    Health, metrics and docs endpoints are always exempt so monitoring never trips
    the limiter.
    """

    EXEMPT_PREFIXES = ("/health", "/healthz", "/readyz", "/metrics", "/docs", "/redoc", "/openapi.json")

    def __init__(self, app, limit: int | None = None, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.limit = limit if limit is not None else settings.rate_limit_per_minute
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.rate_limit_enabled or request.url.path.startswith(self.EXEMPT_PREFIXES):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = self._hits[client_ip]
        while bucket and bucket[0] <= now - self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            metrics.inc("mandate_rate_limited_total")
            retry_after = int(self.window - (now - bucket[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "retry_after_seconds": retry_after},
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)
        response = await call_next(request)
        remaining = max(0, self.limit - len(bucket))
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
