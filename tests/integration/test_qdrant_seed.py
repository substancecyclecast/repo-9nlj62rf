import pytest

from snabagent.agents.tools.nsi_search import nsi_search


@pytest.mark.asyncio
async def test_nsi_search_returns_matches():
    results = await nsi_search("швеллер 14 ст3пс", top_k=5)
    assert results
    assert any("MET-SHV-14" in (r["sku"] or "") for r in results)
