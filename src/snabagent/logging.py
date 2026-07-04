"""structlog-конфигурация. JSON-логи в stdout. PII маскируется во всех записях."""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def _mask_processor(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Маскирование PII (e-mail, телефоны, ИНН) в JSON-логах."""
    from .llm.pii_masker import mask_pii

    for k, v in list(event_dict.items()):
        if isinstance(v, str) and len(v) < 10_000:
            masked, _ = mask_pii(v)
            if masked != v:
                event_dict[k] = masked
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _mask_processor,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    _init_sentry()


def _init_sentry() -> None:
    """Опциональная инициализация Sentry — только если задан settings.sentry_dsn."""
    try:
        from .settings import settings
    except Exception:  # pragma: no cover
        return
    dsn = settings.sentry_dsn
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=settings.app_env,
            release="snabagent@0.1.0",
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        )
    except ImportError:  # pragma: no cover
        # Sentry — опциональный prod-dep; в dev/test просто пропускаем.
        pass


log = structlog.get_logger()
