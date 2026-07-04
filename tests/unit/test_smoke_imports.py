"""Smoke-тесты: убеждаемся, что все модули корректно импортируются.

Покрывает большой объём кода тривиальным импортом — не заменяет полноценные
тесты, но защищает от регрессий «забыли поправить импорт».
"""
from __future__ import annotations

import importlib

import pytest

MODULES = [
    "snabagent.settings",
    "snabagent.logging",
    "snabagent.llm.base",
    "snabagent.llm.fake",
    "snabagent.llm.pii_masker",
    "snabagent.llm.router",
    "snabagent.llm.yandex",
    "snabagent.llm.gigachat",
    "snabagent.llm.llama",
    "snabagent.llm.openai",
    "snabagent.db.models",
    "snabagent.db.session",
    "snabagent.db.seed",
    "snabagent.db.repositories",
    "snabagent.vector.embeddings",
    "snabagent.vector.nsi_index",
    "snabagent.vector.supplier_index",
    "snabagent.vector.qdrant_client",
    "snabagent.audit.logger",
    "snabagent.email_service.sender",
    "snabagent.email_service.parser",
    "snabagent.email_service.imap_poller",
    "snabagent.agents.state",
    "snabagent.agents.planner",
    "snabagent.agents.sourcer",
    "snabagent.agents.communicator",
    "snabagent.agents.negotiator",
    "snabagent.agents.verifier",
    "snabagent.agents.reporter",
    "snabagent.agents.graph",
    "snabagent.agents.tools.nsi_search",
    "snabagent.agents.tools.regulatory_filter",
    "snabagent.agents.tools.spark_mock",
    "snabagent.agents.tools.historical",
    "snabagent.agents.tools.pdf_extractor",
    "snabagent.agents.tools.web_scraper",
    "snabagent.agents.prompts",
    "snabagent.tasks.celery_app",
    "snabagent.tasks.lot_pipeline",
    "snabagent.tasks.emails",
    "snabagent.parsers",
    "snabagent.parsers.docx",
    "snabagent.parsers.pdf",
    "snabagent.parsers.generic",
    "snabagent.utils.id",
    "snabagent.utils.retry",
    "snabagent.utils.time",
    "snabagent.api.main",
    "snabagent.api.schemas",
    "snabagent.api.ws",
    "snabagent.api.routes.lots",
    "snabagent.api.routes.audit",
    "snabagent.api.routes.webhooks",
]


@pytest.mark.parametrize("mod", MODULES)
def test_module_imports(mod: str) -> None:
    importlib.import_module(mod)


def test_extract_text_from_path_unknown_suffix(tmp_path) -> None:
    from snabagent.parsers import extract_text_from_path

    f = tmp_path / "x.txt"
    f.write_text("Hello, мир", encoding="utf-8")
    assert "мир" in extract_text_from_path(str(f))
    assert extract_text_from_path(str(tmp_path / "missing.bin")) == ""


def test_utils_id_short_lot_id() -> None:
    from uuid import uuid4

    from snabagent.utils.id import short_lot_id

    u = uuid4()
    s = short_lot_id(u)
    assert len(s) == 8 and "-" not in s


def test_logging_setup() -> None:
    from snabagent.logging import configure_logging, log

    configure_logging("INFO")
    log.info("smoke test", extra_field="ok")


def test_celery_app_factory() -> None:
    from snabagent.tasks.celery_app import celery_app

    assert celery_app is not None


def test_retry_factory() -> None:
    from snabagent.utils.retry import default_retrying

    r = default_retrying(max_attempts=2)
    assert r is not None


def test_spark_mock_load_search() -> None:
    import asyncio

    from snabagent.agents.tools.spark_mock import search_by_okved

    rows = asyncio.run(search_by_okved(["27.10"]))
    assert isinstance(rows, list)


def test_regulatory_filter_paths() -> None:
    from snabagent.agents.tools.regulatory_filter import check

    assert check({"phase": "pre_nmck", "category": "mro"}).allowed
    assert not check({"phase": "post_tender_published", "category": "mro"}).allowed
    assert not check({"phase": "pre_nmck", "category": "unknown_xxx"}).allowed
