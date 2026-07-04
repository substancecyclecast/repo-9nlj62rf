from snabagent.agents.tools.regulatory_filter import check


def test_blocks_post_tender():
    res = check({"phase": "post_tender_published", "category": "metals"})
    assert res.allowed is False


def test_blocks_unknown_category():
    res = check({"phase": "pre_nmck", "category": "weapons"})
    assert res.allowed is False


def test_allows_normal():
    res = check({"phase": "pre_nmck", "category": "metals"})
    assert res.allowed is True


def test_blocks_unregulated_overflow():
    res = check({"phase": "unregulated", "category": "metals", "total_estimated_rub": 5_000_000})
    assert res.allowed is False
