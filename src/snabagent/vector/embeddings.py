"""Слой эмбеддингов с тремя бэкендами: fake | sentence-transformers | yandex.

`fake` использует детерминированный хеш + bag-of-trigrams. Не требует PyTorch,
работает в оффлайне, достаточно репрезентативный для семантического поиска по
коротким текстам в данном MVP-сценарии.
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

from ..settings import settings

_RUS_WORD_RE = re.compile(r"[\w]+", flags=re.UNICODE)


# ---------------------------------------------------------------------
# Fake-эмбеддер: bag-of-trigrams hashed в N измерений + L2-нормализация.
# ---------------------------------------------------------------------
def _fake_vector(text: str, dim: int) -> list[float]:
    text = text.lower().strip()
    tokens = _RUS_WORD_RE.findall(text)
    grams: list[str] = []
    for t in tokens:
        t_ = f" {t} "
        for i in range(len(t_) - 2):
            grams.append(t_[i : i + 3])
        # сами слова тоже полезны
        grams.append(t)
    vec = [0.0] * dim
    if not grams:
        return vec
    for g in grams:
        h = int.from_bytes(hashlib.blake2b(g.encode("utf-8"), digest_size=8).digest(), "big")
        idx = h % dim
        sign = 1 if (h >> 32) & 1 else -1
        vec[idx] += sign
    # L2-нормализация
    n = math.sqrt(sum(v * v for v in vec))
    if n == 0:
        return vec
    return [v / n for v in vec]


@lru_cache(maxsize=1)
def _st_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def embed_passages(texts: list[str]) -> list[list[float]]:
    if settings.embedding_backend == "fake":
        return [_fake_vector(t, settings.embedding_dim) for t in texts]
    if settings.embedding_backend == "sentence-transformers":
        prefixed = [f"passage: {t}" for t in texts]
        return _st_model().encode(prefixed, normalize_embeddings=True).tolist()
    raise NotImplementedError(f"Embedding backend {settings.embedding_backend} not supported here")


def embed_queries(texts: list[str]) -> list[list[float]]:
    if settings.embedding_backend == "fake":
        return [_fake_vector(t, settings.embedding_dim) for t in texts]
    if settings.embedding_backend == "sentence-transformers":
        prefixed = [f"query: {t}" for t in texts]
        return _st_model().encode(prefixed, normalize_embeddings=True).tolist()
    raise NotImplementedError(f"Embedding backend {settings.embedding_backend} not supported here")


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    num = sum(x * y for x, y in zip(a, b, strict=False))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)
