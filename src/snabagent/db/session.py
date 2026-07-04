"""Создание async engine + sessionmaker."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..settings import settings

_url = str(settings.database_url)
_is_sqlite = _url.startswith("sqlite")
_engine_kwargs: dict = {"echo": False, "future": True}
if not _is_sqlite:
    _engine_kwargs.update(pool_size=20, max_overflow=20, pool_pre_ping=True, pool_recycle=1800)

engine = create_async_engine(_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:  # FastAPI Depends
    async with AsyncSessionLocal() as session:
        yield session
