"""Индексация НСИ + поставщиков в векторное хранилище."""
from __future__ import annotations

import asyncio

from snabagent.vector.nsi_index import reindex_nsi
from snabagent.vector.supplier_index import reindex_suppliers


async def main():
    n = await reindex_nsi()
    m = await reindex_suppliers()
    print(f"NSI uploaded: {n}, suppliers uploaded: {m}")


if __name__ == "__main__":
    asyncio.run(main())
