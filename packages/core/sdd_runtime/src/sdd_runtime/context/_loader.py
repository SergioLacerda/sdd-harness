"""ContextLoader — on-demand, budget-aware, artifact-backed context loading."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from sdd_runtime.exceptions import BudgetBreachError as BudgetBreachError

from ..cache import cached_load, get_context_cache
from ._matching import _match_items as _match_items_impl
from ._matching import _render_item as _render_item_impl
from ._request import ContextRequest
from ._result import ContextResult

if TYPE_CHECKING:
    from ..intelligence import ProviderRegistry

logger = logging.getLogger(__name__)


class ContextLoader:
    """Loads governance context on demand from a compiled artifact.

    When an artifact is provided, items are matched by ID prefix or title
    substring (case-insensitive).  When no artifact is provided the loader
    falls back to a deterministic stub so callers always receive a response.

    Caching is enabled by default via in-memory LRU cache (128 entries, 5-min TTL).
    """

    # Global cache instance
    _cache = get_context_cache()

    _render_item = staticmethod(_render_item_impl)
    _match_items = staticmethod(_match_items_impl)

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        """Initialize ContextLoader with optional IntelligenceProvider registry.

        Args:
            registry: ProviderRegistry for context compression at YELLOW zone.
                     If None, builds a default registry with priority chain:
                     HttpProvider → AstProvider → TfidfProvider → LocalIntelligenceProvider.
        """
        self._registry: ProviderRegistry | None = registry

    @property
    def registry(self) -> ProviderRegistry:
        """Lazy-init provider registry (O6) only when context compression is actually needed."""
        if self._registry:
            return self._registry

        # Lazy imports and instantiation
        from ..intelligence import ProviderRegistry
        from ..providers import AstProvider, TfidfProvider

        # HttpProvider is async-only and not compatible with the sync ProviderRegistry.
        # Use CompiledArtifact.from_sdd_compiled_dir_async or HttpProvider directly
        # in async callers.
        self._registry = ProviderRegistry([AstProvider(), TfidfProvider()])
        return self._registry

    def load(self, request: ContextRequest) -> list[str]:
        """Return up to *max_items* context strings for the given query.

        Preserves backward-compatible return type (``list[str]``).
        Call :meth:`load_result` for the richer :class:`ContextResult`.
        """
        return cast(ContextResult, self.load_result(request)).items

    @cached_load(_cache)
    def load_result(self, request: ContextRequest) -> ContextResult:
        """Return a :class:`ContextResult` with full metadata.

        Raises
        ------
        BudgetBreachError
            When ``request.budget_utilization_pct`` is ≥ 100.  Callers MUST
            catch this and escalate to a human checkpoint — no further context
            loading is permitted in this session (§economy/execution-budget.md).
        """
        if (
            request.budget_utilization_pct is not None
            and request.budget_utilization_pct >= 100.0
        ):
            raise BudgetBreachError(
                utilization_pct=request.budget_utilization_pct,
            )

        query = request.query.strip()
        if not query:
            return ContextResult(
                items=[], source="fallback", matched=0, truncated=False
            )

        artifact = request.artifact
        if artifact is None:
            # Deterministic fallback — always resolves cleanly.
            stub = f"context:{query}"
            return ContextResult(
                items=[stub],
                source="fallback",
                matched=1,
                truncated=False,
                bytes_loaded=len(stub.encode()),
            )

        matched = self._match_items(artifact, query, request.item_types)
        limit = max(1, request.max_items)
        truncated = len(matched) > limit
        selected = matched[:limit]
        lines = [
            self._render_item(
                item,
                request.budget_utilization_pct,
                prefer_full_summary=request.prefer_full_summary,
            )
            for item in selected
        ]
        bytes_loaded = sum(len(line.encode()) for line in lines)

        # Attempt compression if in YELLOW zone (70-90% utilization)
        compression_ratio: float | None = None
        if (
            request.budget_utilization_pct is not None
            and 70.0 <= request.budget_utilization_pct < 100.0
        ):
            try:
                from ..intelligence import ContextBundle

                # Compute target budget in bytes: if loaded=1000 and util=80%, target 70% util
                # Target bytes = loaded * (70 / utilization)
                target_budget_bytes = int(
                    bytes_loaded * (70.0 / request.budget_utilization_pct)
                )
                bundle = ContextBundle(
                    items=lines, query=query, budget_bytes=max(1, target_budget_bytes)
                )
                compressed = self.registry.compress_context(bundle)
                if compressed.compression_ratio < 1.0:
                    lines = compressed.items
                    bytes_loaded = compressed.compressed_bytes
                    compression_ratio = compressed.compression_ratio
                    logger.debug(
                        "Applied compression at YELLOW zone (%.1f%% utilization): "
                        "ratio=%.2f, items=%d→%d",
                        request.budget_utilization_pct,
                        compression_ratio,
                        len(selected),
                        len(lines),
                    )
            except Exception as exc:
                logger.debug("Compression failed at YELLOW zone: %s", exc)

        return ContextResult(
            items=lines,
            source="artifact",
            matched=len(matched),
            truncated=truncated,
            bytes_loaded=bytes_loaded,
            compression_ratio=compression_ratio,
        )
