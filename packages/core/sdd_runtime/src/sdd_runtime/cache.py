"""
Runtime Context Caching — In-Memory LRU Cache for Hot Queries

Provides in-memory caching for frequently accessed governance artifacts to reduce
I/O overhead and improve latency for repeated context loading requests.

Cache policy:
  - Max size: 128 artifacts
  - TTL: 5 minutes
  - Eviction: LRU (Least Recently Used)
  - Key: hash(artifact_id, query, max_items, item_types)
"""

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


@dataclass
class CacheEntry:
    """Single cache entry with timestamp"""

    result: Any  # ContextResult type at runtime
    timestamp: float
    ttl_seconds: int = 300  # 5 minutes


class ContextCache:
    """In-memory LRU cache for ContextLoader results"""

    def __init__(self, max_size: int = 128, ttl_seconds: int = 300):
        """Initialize cache

        Args:
            max_size: Maximum number of cached results (default: 128)
            ttl_seconds: Time-to-live for cache entries in seconds (default: 300 / 5 min)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: dict[str, CacheEntry] = {}
        self.hit_count = 0
        self.miss_count = 0

    @staticmethod
    def _make_key(
        artifact_id: str | None,
        query: str,
        max_items: int,
        item_types: list[str],
        budget_utilization_pct: float = 0.0,
    ) -> str:
        """Generate cache key from request parameters

        Args:
            artifact_id: Compiled artifact ID (or None for fallback)
            query: Search query string
            max_items: Maximum items to return
            item_types: Item type filters
            budget_utilization_pct: Budget utilization percentage (affects compression)

        Returns:
            Hash-based cache key
        """
        key_str = f"{artifact_id}:{query}:{max_items}:{','.join(sorted(item_types))}:{budget_utilization_pct:.1f}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        artifact_id: str | None,
        query: str,
        max_items: int,
        item_types: list[str],
        budget_utilization_pct: float = 0.0,
    ) -> Any | None:
        """Retrieve cached result if valid

        Args:
            artifact_id: Artifact ID for lookup
            query: Search query
            max_items: Max items requested
            item_types: Item type filters
            budget_utilization_pct: Budget utilization percentage (affects compression)

        Returns:
            Cached ContextResult if hit and not expired, else None
        """
        key = self._make_key(
            artifact_id, query, max_items, item_types, budget_utilization_pct
        )
        entry = self.cache.get(key)

        if entry is None:
            self.miss_count += 1
            return None

        # Check TTL
        elapsed = time.time() - entry.timestamp
        if elapsed > entry.ttl_seconds:
            # Expired, remove and return miss
            del self.cache[key]
            self.miss_count += 1
            return None

        self.hit_count += 1
        return entry.result

    def set(
        self,
        artifact_id: str | None,
        query: str,
        max_items: int,
        item_types: list[str],
        result: Any,
        budget_utilization_pct: float = 0.0,
    ) -> None:
        """Cache a result

        Args:
            artifact_id: Artifact ID for storage
            query: Search query
            max_items: Max items
            item_types: Item type filters
            result: ContextResult to cache
            budget_utilization_pct: Budget utilization percentage (affects compression)
        """
        key = self._make_key(
            artifact_id, query, max_items, item_types, budget_utilization_pct
        )

        # Simple LRU: if at capacity, remove oldest entry
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].timestamp,
            )
            del self.cache[oldest_key]

        self.cache[key] = CacheEntry(
            result=result,
            timestamp=time.time(),
            ttl_seconds=self.ttl_seconds,
        )

    def stats(self) -> dict[str, Any]:
        """Get cache statistics

        Returns:
            Dict with hit/miss counts and hit rate
        """
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0.0

        return {
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate_pct": hit_rate,
            "entries": len(self.cache),
            "max_size": self.max_size,
        }

    def clear(self) -> None:
        """Clear all cached entries"""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0


def cached_load(cache_obj: ContextCache) -> Callable[..., Any]:
    """Decorator to add caching to ContextLoader.load_result

    Args:
        cache_obj: ContextCache instance to use

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, request: Any) -> Any:
            # Get artifact ID if available
            artifact_id: str | None = None
            if request.artifact is not None:
                # Use artifact's ID if available, otherwise generate one
                attr_id = getattr(request.artifact, "artifact_id", None)
                artifact_id = (
                    str(attr_id) if attr_id is not None else str(id(request.artifact))
                )

            # Get budget utilization percentage from request
            budget_utilization_pct = getattr(request, "budget_utilization_pct", 0.0)
            if budget_utilization_pct is None:
                budget_utilization_pct = 0.0

            # Try cache
            cached = cache_obj.get(
                artifact_id,
                request.query,
                request.max_items,
                request.item_types,
                budget_utilization_pct,
            )
            if cached is not None:
                return cached

            # Cache miss — call original function
            result = func(self, request)

            # Cache the result
            cache_obj.set(
                artifact_id,
                request.query,
                request.max_items,
                request.item_types,
                result,
                budget_utilization_pct,
            )

            return result

        return wrapper

    return decorator


# Global cache instance
_context_cache = ContextCache(max_size=128, ttl_seconds=300)


def get_context_cache() -> ContextCache:
    """Get the global context cache instance

    Returns:
        Global ContextCache instance
    """
    return _context_cache
