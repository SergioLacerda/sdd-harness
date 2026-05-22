"""Pluggable Intelligence Providers — Phase 5.

Defines the IntelligenceProvider Protocol and the data types for task
analysis, context compression, and budget estimation.  Provides a
LocalIntelligenceProvider (grep + heuristics, always available, offline-
capable) and a ProviderRegistry that guarantees graceful degradation: the
system always functions without any external provider.

Architecture:

    ProviderRegistry → tries providers in order → falls back to LocalIntelligenceProvider
    IntelligenceProvider (Protocol) ← LocalIntelligenceProvider  (always available)
                                    ← (future: Semantic, AST, External providers)

Graceful degradation contract (§economy/efficiency-policy.md):
    The system MUST function with only the built-in local provider in place.
    External providers augment quality but are never required for correctness.

Reference: .sdd/runtime analytics design §Phase 5
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class TaskContext:
    """Input to :meth:`IntelligenceProvider.analyze_task` and
    :meth:`IntelligenceProvider.estimate_budget`.

    Attributes
    ----------
    query:
        Task description or user instruction text.
    path_id:
        Active PATH classification ("A" | "B" | "C" | "D"); empty when not
        yet classified.
    context_bytes_loaded:
        Bytes already loaded into the context window, if known.
    context_budget_bytes:
        Total context budget ceiling for the current PATH, if known.
    """

    query: str
    path_id: str = ""
    context_bytes_loaded: int | None = None
    context_budget_bytes: int | None = None


@dataclass
class AnalysisResult:
    """Output of :meth:`IntelligenceProvider.analyze_task`.

    Attributes
    ----------
    task_class:
        Detected task category: ``"bug-fix"``, ``"feature"``, ``"refactor"``,
        ``"test"``, ``"docs"``, or ``"unknown"``.
    complexity_score:
        Estimated complexity in the range 0.0–1.0.
    suggested_path_id:
        Recommended PATH based on task class and complexity.
    keywords:
        Matched keywords that drove the classification (deduplicated).
    provider:
        Name of the provider that produced this result.
    """

    task_class: str
    complexity_score: float
    suggested_path_id: str
    keywords: list[str]
    provider: str


@dataclass
class ContextBundle:
    """Input to :meth:`IntelligenceProvider.compress_context`.

    Attributes
    ----------
    items:
        Raw context strings to compress.
    query:
        The query these items were loaded for (used by semantic providers).
    budget_bytes:
        Target size in bytes after compression.
    """

    items: list[str]
    query: str
    budget_bytes: int


@dataclass
class CompressedContext:
    """Output of :meth:`IntelligenceProvider.compress_context`.

    Attributes
    ----------
    items:
        Compressed context strings.
    original_bytes:
        Total UTF-8 bytes of the input items.
    compressed_bytes:
        Total UTF-8 bytes of the output items.
    compression_ratio:
        ``compressed_bytes / original_bytes``; 1.0 means no reduction.
    provider:
        Name of the provider that produced this result.
    """

    items: list[str]
    original_bytes: int
    compressed_bytes: int
    compression_ratio: float
    provider: str


@dataclass
class BudgetEstimate:
    """Output of :meth:`IntelligenceProvider.estimate_budget`.

    Attributes
    ----------
    estimated_bytes:
        Predicted context bytes required for the task.
    suggested_path_id:
        PATH that best fits the estimated size.
    confidence:
        Estimate confidence in range 0.0–1.0.
    provider:
        Name of the provider that produced this result.
    """

    estimated_bytes: int
    suggested_path_id: str
    confidence: float
    provider: str


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class IntelligenceProvider(Protocol):
    """Interface for cognitive intelligence providers.

    All methods MUST be safe to call unconditionally — providers that cannot
    fulfil a request should return a best-effort degraded result, never raise.
    The ``available`` property allows :class:`ProviderRegistry` to skip
    unavailable providers before attempting a call.
    """

    @property
    def name(self) -> str:
        """Stable identifier for this provider (echoed in result fields)."""
        pass

    @property
    def available(self) -> bool:
        """True when this provider can currently service requests."""
        pass

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        """Analyse a task context and return classification + complexity."""
        pass

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        """Compress a context bundle to fit within ``context.budget_bytes``."""
        pass

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        """Estimate the context bytes required for the given task."""
        pass


# ---------------------------------------------------------------------------
# Heuristic constants for LocalIntelligenceProvider
# ---------------------------------------------------------------------------

# Task class keyword table — first match wins (order matters).
_TASK_CLASS_KEYWORDS: dict[str, list[str]] = {
    "bug-fix": ["fix", "bug", "error", "crash", "fail", "broken", "issue", "wrong"],
    "feature": ["add", "implement", "create", "new", "feature", "build", "introduce"],
    "refactor": [
        "refactor",
        "restructure",
        "rename",
        "move",
        "clean",
        "reorganize",
        "extract",
    ],
    "test": ["test", "spec", "coverage", "assert", "mock", "fixture"],
    "docs": ["doc", "readme", "explain", "comment", "document", "describe"],
}

# Complexity bands based on query character length.
_COMPLEXITY_LOW_THRESHOLD: int = 50  # < 50 chars  → low   (0.2)
_COMPLEXITY_HIGH_THRESHOLD: int = 200  # > 200 chars → high  (0.8)
_COMPLEXITY_LOW: float = 0.2
_COMPLEXITY_MED: float = 0.5
_COMPLEXITY_HIGH: float = 0.8

# PATH suggestion table: (task_class, complexity_band) → path_id.
_PATH_SUGGESTION: dict[tuple[str, str], str] = {
    ("bug-fix", "low"): "A",
    ("bug-fix", "medium"): "A",
    ("bug-fix", "high"): "B",
    ("test", "low"): "A",
    ("test", "medium"): "B",
    ("docs", "low"): "A",
    ("docs", "medium"): "A",
}
_PATH_HIGH_COMPLEXITY: str = "C"  # any task class at high complexity → PATH C

# Budget estimation constants.
_BYTES_PER_QUERY_CHAR: int = 8  # rough heuristic: 8 bytes of context per query char
_BUDGET_MIN_BYTES: int = 5 * 1024  # 5 KB floor
_BUDGET_MAX_BYTES: int = 85 * 1024  # 85 KB ceiling (PATH C)
_LOCAL_CONFIDENCE: float = 0.4  # heuristic estimate; low confidence

# PATH suggestion from estimated budget size.
_PATH_FROM_BUDGET: list[tuple[int, str]] = [
    (40 * 1024, "A"),
    (45 * 1024, "B"),
    (85 * 1024, "C"),
]


# ---------------------------------------------------------------------------
# Local provider
# ---------------------------------------------------------------------------


class LocalIntelligenceProvider:
    """Heuristic-based intelligence provider using keyword matching and size rules.

    Always available (no external dependencies, no I/O, no network).
    Provides baseline quality for PATH routing, context compression, and
    budget estimation that is sufficient for correct harness operation.
    """

    @property
    def name(self) -> str:
        """Name."""
        return "local"

    @property
    def available(self) -> bool:
        """Available."""
        return True

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        """Classify the task with keyword heuristics and query length scoring.

        Task class: first keyword match wins.  Complexity: derived from the
        number of characters in ``task.query``.  Suggested PATH: table lookup
        with a hard override to PATH C for high-complexity tasks.
        """
        query_lower = task.query.lower()

        # 1. Task class via keyword matching.
        task_class = "unknown"
        matched_keywords: list[str] = []
        for cls, kws in _TASK_CLASS_KEYWORDS.items():
            hits = [kw for kw in kws if kw in query_lower]
            if hits:
                task_class = cls
                matched_keywords = hits
                break

        # 2. Complexity from query length.
        q_len = len(task.query)
        if q_len < _COMPLEXITY_LOW_THRESHOLD:
            complexity = _COMPLEXITY_LOW
            band = "low"
        elif q_len <= _COMPLEXITY_HIGH_THRESHOLD:
            complexity = _COMPLEXITY_MED
            band = "medium"
        else:
            complexity = _COMPLEXITY_HIGH
            band = "high"

        # 3. Suggested PATH.
        if band == "high":
            suggested_path = _PATH_HIGH_COMPLEXITY
        else:
            suggested_path = _PATH_SUGGESTION.get((task_class, band), "B")

        return AnalysisResult(
            task_class=task_class,
            complexity_score=complexity,
            suggested_path_id=suggested_path,
            keywords=list(dict.fromkeys(matched_keywords)),  # dedup, preserve order
            provider=self.name,
        )

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        """Compress context by deduplicating then truncating to budget_bytes.

        Strategy:
        1. Remove exact-duplicate items (first occurrence wins).
        2. Drop items from the end until accumulated size ≤ ``budget_bytes``.
        """
        # Deduplicate preserving insertion order.
        seen: set[str] = set()
        deduped: list[str] = []
        for item in context.items:
            if item not in seen:
                seen.add(item)
                deduped.append(item)

        original_bytes = sum(len(item.encode()) for item in context.items)

        # Truncate to budget — always include the first item even if oversized.
        compressed: list[str] = []
        accumulated = 0
        for item in deduped:
            item_bytes = len(item.encode())
            if accumulated + item_bytes > context.budget_bytes and compressed:
                break
            compressed.append(item)
            accumulated += item_bytes

        compressed_bytes = sum(len(item.encode()) for item in compressed)
        ratio = compressed_bytes / original_bytes if original_bytes > 0 else 1.0

        return CompressedContext(
            items=compressed,
            original_bytes=original_bytes,
            compressed_bytes=compressed_bytes,
            compression_ratio=round(ratio, 4),
            provider=self.name,
        )

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        """Estimate context bytes from query length × heuristic multiplier.

        Clamps the result between 5 KB (minimum) and 85 KB (PATH C ceiling).
        Confidence is intentionally low (0.4) — this baseline is sufficient
        for routing; semantic providers yield higher-confidence estimates.
        """
        raw = len(task.query) * _BYTES_PER_QUERY_CHAR
        estimated = max(_BUDGET_MIN_BYTES, min(raw, _BUDGET_MAX_BYTES))

        suggested_path = "C"  # default for large estimates
        for ceiling, path in _PATH_FROM_BUDGET:
            if estimated <= ceiling:
                suggested_path = path
                break

        return BudgetEstimate(
            estimated_bytes=estimated,
            suggested_path_id=suggested_path,
            confidence=_LOCAL_CONFIDENCE,
            provider=self.name,
        )


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------


class ProviderRegistry:
    """Orchestrates intelligence providers with graceful degradation.

    Providers are tried in registration order; the first ``available`` one
    wins.  When no registered provider is available the registry falls back
    to the built-in :class:`LocalIntelligenceProvider`, which is always
    available.

    This invariant guarantees that :meth:`analyze_task`,
    :meth:`compress_context`, and :meth:`estimate_budget` never raise due
    to provider unavailability.

    Parameters
    ----------
    providers:
        Ordered list of providers to try before the local fallback.  Pass
        ``None`` or an empty list to use only the local provider.
    """

    def __init__(
        self,
        providers: list[IntelligenceProvider] | None = None,
    ) -> None:
        self._providers: list[IntelligenceProvider] = list(providers or [])
        self._local = LocalIntelligenceProvider()

    def _active(self) -> IntelligenceProvider:
        """Return the first available provider; fall back to local."""
        for p in self._providers:
            if p.available:
                return p
        return self._local

    @property
    def active_provider(self) -> str:
        """Name of the provider that will handle the next request."""
        return self._active().name

    def analyze_task(self, task: TaskContext) -> AnalysisResult:
        """Analyze Task."""
        return self._active().analyze_task(task)

    def compress_context(self, context: ContextBundle) -> CompressedContext:
        """Compress Context."""
        return self._active().compress_context(context)

    def estimate_budget(self, task: TaskContext) -> BudgetEstimate:
        """Estimate Budget."""
        return self._active().estimate_budget(task)
