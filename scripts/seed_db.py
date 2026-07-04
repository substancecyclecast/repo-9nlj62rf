"""Заполняет БД из data/*.csv (создаёт customer SIBUR Demo + NSI + suppliers)."""
from __future__ import annotations

import asyncio

from snabagent.db.seed import seed_all


def main() -> None:
    asyncio.run(seed_all())
    print("DB seeded")


if __name__ == "__main__":
    main()
