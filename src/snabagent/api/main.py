"""FastAPI приложение SnabAgent.

Routes (v1):
- POST /api/v1/lots                — создаёт лот, запускает граф в фоне
- GET  /api/v1/lots/               — список лотов
- GET  /api/v1/lots/{lot_id}       — детали + parsed_items + final_report
- GET  /api/v1/lots/{lot_id}/audit — audit-log
- POST /api/v1/lots/{lot_id}/approve — одобрить лот, выбрать поставщика
- POST /api/v1/webhooks/email-in   — приём писем от Mailcow
- POST /api/v1/webhooks/telegram   — Telegram bot webhook
- GET  /health, /health/live, /health/ready
- WS   /ws/lots/{lot_id}
"""
from __future__ import annotations

import asyncio
import signal
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from ..db.models import Base
from ..db.session import engine
from ..logging import configure_logging
from ..settings import settings
from .auth import require_api_key
from .metrics import PrometheusMiddleware
from .routes import audit, export, health, lots, webhooks, websocket
from .routes import auth as auth_route
from .routes import metrics as metrics_route
from .sso import oauth2 as sso_oauth2
from .sso import saml as sso_saml
from .ws import bus  # noqa: F401 — singleton

logger = structlog.get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

_shutdown_event = asyncio.Event()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Add request_id to every request for tracing."""

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    configure_logging(settings.log_level)

    # Sentry integration (production monitoring)
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.app_env,
                traces_sample_rate=0.2 if settings.app_env == "prod" else 1.0,
                profiles_sample_rate=0.1,
                integrations=[FastApiIntegration(), SqlalchemyIntegration()],
                send_default_pii=False,
            )
            logger.info("sentry_initialized", dsn_prefix=settings.sentry_dsn[:20])
        except ImportError:
            logger.warning("sentry_sdk not installed, skipping Sentry init")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Наполняем справочник НСИ/поставщиков и переиндексируем вектор-хранилище,
    # чтобы планировщик мог сопоставлять позиции (особенно с in-memory fallback,
    # который пуст после каждого рестарта процесса).
    try:
        from ..db.seed import seed_all
        from ..vector.nsi_index import reindex_nsi
        from ..vector.supplier_index import reindex_suppliers

        await seed_all()
        n = await reindex_nsi()
        m = await reindex_suppliers()
        logger.info("vector_store_indexed", nsi=n, suppliers=m)
    except Exception as e:  # noqa: BLE001 - стартап не должен падать из-за сидов
        logger.warning("vector_reindex_failed", error=str(e))

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _shutdown_event.set)
    yield
    _shutdown_event.set()


app = FastAPI(
    title="SnabAgent API",
    version="2.2.0",
    description="Автономный мульти-агентный сервис промышленных закупок.",
    lifespan=lifespan,
    dependencies=[Depends(require_api_key)],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Request ID middleware
app.add_middleware(RequestIdMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Prometheus middleware
app.add_middleware(PrometheusMiddleware)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("unhandled_exception", request_id=request_id, error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


# Health endpoints (outside /api/v1, standard practice)
@app.get("/health")
async def root_health():
    return {"status": "ok", "service": "snabagent", "env": settings.app_env}


# Mount all routers under /api/v1
from fastapi import APIRouter  # noqa: E402

v1 = APIRouter(prefix="/api/v1")
v1.include_router(lots.router)
v1.include_router(audit.router)
v1.include_router(webhooks.router)
v1.include_router(auth_route.router)
v1.include_router(metrics_route.router)
v1.include_router(export.router)
v1.include_router(sso_saml.router)
v1.include_router(sso_oauth2.router)

# Telegram webhook router
from .routes.telegram_webhook import router as telegram_router  # noqa: E402

v1.include_router(telegram_router)

app.include_router(v1)

# Health and websocket remain outside versioned prefix
app.include_router(health.router)
app.include_router(websocket.router)

# Static frontend serving (SPA fallback) — MUST be after all API routers
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIR.exists():
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    _ASSETS_DIR = _FRONTEND_DIR / "assets"
    if _ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="assets")

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        file_path = _FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_FRONTEND_DIR / "index.html"))
