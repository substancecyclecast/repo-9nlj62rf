"""pytest fixtures: оффлайн-окружение (SQLite + FakeLLM + Fake embeddings)."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Окружение для всех тестов
os.environ["APP_ENV"] = "dev"
os.environ["LLM_PRIMARY"] = "fake"
os.environ["LLM_FALLBACK"] = "fake"
os.environ["LLM_VERIFIER"] = "fake"
os.environ["LLM_VERIFIER_FALLBACK"] = "fake"
os.environ["EMBEDDING_BACKEND"] = "fake"
os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./.pytest_snabagent.db"

import pytest  # noqa: E402

from snabagent.db.models import Base  # noqa: E402
from snabagent.db.seed import seed_all  # noqa: E402
from snabagent.db.session import engine  # noqa: E402
from snabagent.vector.nsi_index import reindex_nsi  # noqa: E402
from snabagent.vector.supplier_index import reindex_suppliers  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _bootstrap(event_loop):
    db_path = Path(".pytest_snabagent.db")
    if db_path.exists():
        db_path.unlink()

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await seed_all()
        await reindex_nsi()
        await reindex_suppliers()

    event_loop.run_until_complete(_setup())
    yield
    if db_path.exists():
        db_path.unlink()


@pytest.fixture(autouse=True)
def _clear_llm_cache():
    """Сбрасываем lru_cache get_llm между тестами, чтобы monkeypatch settings срабатывал."""
    from snabagent.llm.router import get_llm

    get_llm.cache_clear()
    yield
    get_llm.cache_clear()
