"""Tests for vector/embeddings modules."""
from __future__ import annotations

from snabagent.vector.embeddings import cosine, embed_passages, embed_queries


def test_embed_passages():
    vecs = embed_passages(["Трубы стальные ГОСТ 10704"])
    assert len(vecs) == 1
    assert isinstance(vecs[0], list)
    assert len(vecs[0]) > 0


def test_embed_queries():
    vecs = embed_queries(["Трубы стальные"])
    assert len(vecs) == 1
    assert isinstance(vecs[0], list)


def test_embed_multiple():
    vecs = embed_passages(["Арматура А500", "Цемент М500", "Кабель ВВГ"])
    assert len(vecs) == 3


def test_cosine_identical():
    v = embed_passages(["test"])[0]
    assert cosine(v, v) > 0.99


def test_cosine_similar():
    v1 = embed_passages(["Трубы стальные 108x4"])[0]
    v2 = embed_passages(["Стальная труба 108 мм"])[0]
    sim = cosine(v1, v2)
    assert sim > 0.0


def test_cosine_empty():
    assert cosine([], []) == 0.0


def test_embed_empty_text():
    vecs = embed_passages([""])
    assert len(vecs) == 1
