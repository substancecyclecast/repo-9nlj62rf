"""Mandate API — FastAPI application entrypoint."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import (
    routes_agent,
    routes_auth,
    routes_ledger,
    routes_ops,
    routes_payments,
    routes_treasury,
)
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure the SQLite data directory exists, create tables, and seed demo data
    # unless explicitly disabled (MANDATE_SEED=0).
    if settings.database_url.startswith("sqlite"):
        path = settings.database_url.replace("sqlite:///", "", 1)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    init_db()
    if os.getenv("MANDATE_SEED", "1") != "0":
        from app.services.seed import seed_demo

        db = SessionLocal()
        try:
            seed_demo(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="Mandate API",
    version=__version__,
    description="Autonomous CFO agent for crypto-native organizations and DAOs.",
    lifespan=lifespan,
)

# Middleware order matters: the outermost added runs first. We add rate limiting
# last so it wraps everything, then request-context for metrics/ids, then CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)

_prefix = settings.api_v1_prefix
app.include_router(routes_auth.router, prefix=_prefix)
app.include_router(routes_treasury.router, prefix=_prefix)
app.include_router(routes_agent.router, prefix=_prefix)
app.include_router(routes_payments.router, prefix=_prefix)
app.include_router(routes_ledger.router, prefix=_prefix)
app.include_router(routes_ops.router, prefix=_prefix)
app.include_router(routes_ops.infra_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "mandate", "version": __version__}


@app.get("/")
def root() -> dict:
    return {
        "name": "Mandate",
        "tagline": "Autonomous CFO agent for crypto-native orgs and DAOs",
        "docs": "/docs",
        "api_prefix": _prefix,
    }
