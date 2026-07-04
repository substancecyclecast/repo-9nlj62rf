"""Test fixtures: isolated in-memory database with seeded demo org."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.seed import seed_demo


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "onchain: marks tests as on-chain integration tests requiring testnet keys",
    )


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def org(db):
    return seed_demo(db, force=True)
