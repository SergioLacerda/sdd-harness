from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sdd_runtime.cache import ContextCache, cached_load


@dataclass
class _Req:
    artifact: Any
    query: str
    max_items: int
    item_types: list[str]
    budget_utilization_pct: float | None = 0.0


class _Loader:
    def __init__(self) -> None:
        self.calls = 0

    def load(self, request: _Req) -> dict[str, Any]:
        self.calls += 1
        return {"q": request.query, "calls": self.calls}


def test_make_key_stable_with_item_type_order() -> None:
    key1 = ContextCache._make_key("a", "q", 1, ["B", "A"], 12.0)
    key2 = ContextCache._make_key("a", "q", 1, ["A", "B"], 12.0)
    assert key1 == key2


def test_cache_get_set_hit_and_miss_and_stats() -> None:
    c = ContextCache(max_size=4, ttl_seconds=60)
    assert c.get("a", "q", 1, ["X"]) is None
    c.set("a", "q", 1, ["X"], {"ok": True})
    got = c.get("a", "q", 1, ["X"])
    assert got == {"ok": True}
    stats = c.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["entries"] == 1


def test_cache_ttl_expiry_and_lru_eviction() -> None:
    c = ContextCache(max_size=2, ttl_seconds=1)
    c.set("a", "q1", 1, ["X"], 1)
    c.set("a", "q2", 1, ["X"], 2)
    time.sleep(1.1)
    assert c.get("a", "q1", 1, ["X"]) is None  # expired path

    c = ContextCache(max_size=2, ttl_seconds=60)
    c.set("a", "q1", 1, ["X"], 1)
    c.set("a", "q2", 1, ["X"], 2)
    c.set("a", "q3", 1, ["X"], 3)  # evicts oldest
    assert c.get("a", "q1", 1, ["X"]) is None
    assert c.get("a", "q3", 1, ["X"]) == 3


def test_cache_clear_resets_all() -> None:
    c = ContextCache()
    c.set("a", "q", 1, ["X"], 1)
    c.get("a", "q", 1, ["X"])
    c.clear()
    assert c.stats()["entries"] == 0
    assert c.stats()["hits"] == 0
    assert c.stats()["misses"] == 0


def test_cached_load_decorator_hits_cache_and_handles_budget_none() -> None:
    cache = ContextCache()
    loader = _Loader()
    wrapped = cached_load(cache)(_Loader.load)

    req = _Req(
        artifact=object(),
        query="q",
        max_items=2,
        item_types=["M"],
        budget_utilization_pct=None,
    )
    first = wrapped(loader, req)
    second = wrapped(loader, req)
    assert first == second
    assert loader.calls == 1
