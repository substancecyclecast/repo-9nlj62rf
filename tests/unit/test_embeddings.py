from snabagent.vector.embeddings import cosine, embed_passages, embed_queries


def test_fake_embed_deterministic():
    v1 = embed_passages(["швеллер 14 ст3пс"])[0]
    v2 = embed_passages(["швеллер 14 ст3пс"])[0]
    assert v1 == v2


def test_relevant_items_score_higher():
    targets = embed_passages(
        ["Швеллер 14 ст3пс", "Арматура А500С d12", "Ноутбук Lenovo ThinkPad T14"]
    )
    q = embed_queries(["швеллер 14-й, трешка"])[0]
    scores = [cosine(q, t) for t in targets]
    # Швеллер должен быть самым близким
    assert scores[0] == max(scores)
