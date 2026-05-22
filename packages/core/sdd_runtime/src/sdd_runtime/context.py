"""Context loading engine — on-demand, budget-aware, artifact-backed."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from .artifacts import CompiledArtifact, GovernanceItem
from .cache import cached_load, get_context_cache

if TYPE_CHECKING:
    from .intelligence import ProviderRegistry

logger = logging.getLogger(__name__)


from sdd_runtime.exceptions import BudgetBreachError as BudgetBreachError  # noqa: E402


@dataclass
class ContextRequest:
    """Specification for a context loading request."""

    query: str
    max_items: int = 5
    artifact: CompiledArtifact | None = None
    item_types: list[str] = field(default_factory=list)  # filter by type if non-empty
    budget_utilization_pct: float | None = (
        None  # current utilization; ≥100 → BREACH block
    )
    prefer_full_summary: bool = (
        False  # if True, GREEN zone prefers summary_full when available
    )


@dataclass
class ContextResult:
    """Result of a context loading operation."""

    items: list[str]
    source: str  # "artifact" | "fallback"
    matched: int
    truncated: bool
    bytes_loaded: int = 0  # total UTF-8 bytes of returned items (§economy/metrics.md)
    compression_ratio: float | None = (
        None  # compression ratio if compression applied; None if not
    )


class ContextLoader:
    """Loads governance context on demand from a compiled artifact.

    When an artifact is provided, items are matched by ID prefix or title
    substring (case-insensitive).  When no artifact is provided the loader
    falls back to a deterministic stub so callers always receive a response.

    Caching is enabled by default via in-memory LRU cache (128 entries, 5-min TTL).
    """

    # Global cache instance
    _cache = get_context_cache()

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
        from .intelligence import ProviderRegistry
        from .providers import AstProvider, TfidfProvider

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
                from .intelligence import ContextBundle

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

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _render_item(
        item: GovernanceItem,
        budget_utilization_pct: float | None,
        *,
        prefer_full_summary: bool = False,
    ) -> str:
        """Render a governance item with budget-aware verbosity.

        Progressive disclosure based on budget utilization zone:
        - RED zone (>90%): summary_minimal (one-liner, ~35 tokens)
        - YELLOW zone (70-90%): summary_runtime (enforcement rules, ~120 tokens)
        - GREEN zone (<70%): id: title (default), optional summary_full
        """
        if budget_utilization_pct is not None:
            summary_minimal = getattr(item, "summary_minimal", None)
            summary_runtime = getattr(item, "summary_runtime", None)
            if budget_utilization_pct > 90.0 and summary_minimal:
                return str(summary_minimal)
            if budget_utilization_pct >= 70.0 and summary_runtime:
                return str(summary_runtime)
        if prefer_full_summary:
            summary_full = getattr(item, "summary_full", None)
            if summary_full:
                return str(summary_full)
        return f"{item.id}: {item.title}"

    @staticmethod
    def _match_items(
        artifact: CompiledArtifact,
        query: str,
        type_filter: list[str],
    ) -> list[GovernanceItem]:
        lower_query = query.lower()
        candidates = artifact.items
        if type_filter:
            upper_types = {t.upper() for t in type_filter}
            candidates = [i for i in candidates if i.item_type.upper() in upper_types]

        # Exact ID match first, then partial matches on ID/title/description.
        exact = [i for i in candidates if i.id.lower() == lower_query]
        if exact:
            return exact

        partial = [
            i
            for i in candidates
            if (
                lower_query in i.id.lower()
                or lower_query in i.title.lower()
                or lower_query in i.description.lower()
            )
        ]
        return partial
