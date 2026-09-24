"""Tiny dependency-free TF-IDF retriever for picking relevant few-shot examples."""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9']+")


def _tok(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class Retriever:
    def __init__(self, docs: list[str]):
        self.docs = docs
        self._tfs = [Counter(_tok(d)) for d in docs]
        df: Counter = Counter()
        for tf in self._tfs:
            df.update(tf.keys())
        n = max(len(docs), 1)
        self._idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self._vecs = [self._vec(tf) for tf in self._tfs]

    def _vec(self, tf: Counter) -> dict[str, float]:
        v = {t: (1 + math.log(c)) * self._idf.get(t, 1.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def top(self, query: str, k: int = 6) -> list[int]:
        """Indices of the k most similar docs (cosine). Ties broken by order."""
        q = self._vec(Counter(_tok(query)))
        scored = []
        for i, v in enumerate(self._vecs):
            if len(q) < len(v):
                s = sum(w * v.get(t, 0.0) for t, w in q.items())
            else:
                s = sum(w * q.get(t, 0.0) for t, w in v.items())
            scored.append((-s, i))
        scored.sort()
        return [i for _, i in scored[:k]]
