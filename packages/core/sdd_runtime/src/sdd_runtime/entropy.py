"""Cognitive entropy scoring — Phase 4 proactive degradation detection.

Implements the composite entropy metric, convergence detection, and cross-session
drift analysis defined in §economy/efficiency-policy.md.

Entropy score formula (§economy/efficiency-policy.md):
    score = retry_count * reflection_count * budget_utilization_pct / 100

When the score exceeds the PATH threshold, the agent should decompose the task
into smaller PATH A/B units rather than continuing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Entropy thresholds per PATH
# Set at 50% of the theoretical maximum:
#   PATH A/D: max = retry_ceil(2) × reflection_ceil(1) × 100/100 = 2.0  → 1.0
#   PATH B/C: max = retry_ceil(3) × reflection_ceil(2) × 100/100 = 6.0  → 3.0
# ---------------------------------------------------------------------------

_PATH_ENTROPY_THRESHOLD: dict[str, float] = {
    "A": 1.0,
    "B": 3.0,
    "C": 3.0,
    "D": 1.0,
}
_DEFAULT_ENTROPY_THRESHOLD: float = 1.0  # most conservative (PATH A)

# ---------------------------------------------------------------------------
# PATH classification — "heavy" paths that indicate broad task scoping
# ---------------------------------------------------------------------------

_HEAVY_PATHS: frozenset[str] = frozenset({"C", "D"})
_OVERLOAD_DOMINANCE_PCT: float = 50.0  # heavy path > 50% of tasks = overloaded

# ---------------------------------------------------------------------------
# Convergence thresholds
# ---------------------------------------------------------------------------

_CONVERGENCE_WINDOW: int = 3
_DIVERGENCE_SLOPE_THRESHOLD: float = 2.0  # pct/step — growing faster = diverging


# ---------------------------------------------------------------------------
# Entropy score
# ---------------------------------------------------------------------------


@dataclass
class EntropyScore:
    """Cognitive entropy measurement for a single task execution.

    Attributes
    ----------
    retry_count:
        Number of retries consumed so far.
    reflection_count:
        Number of reflection cycles consumed so far.
    budget_utilization_pct:
        Context budget utilization percentage (0–100+).
    path_id:
        Active PATH identifier ("A" | "B" | "C" | "D").
    score:
        Composite entropy score: ``retry_count × reflection_count ×
        budget_utilization_pct / 100``.
    """

    retry_count: int
    reflection_count: int
    budget_utilization_pct: float
    path_id: str
    score: float

    @classmethod
    def compute(
        cls,
        retry_count: int,
        reflection_count: int,
        budget_utilization_pct: float,
        path_id: str = "",
    ) -> EntropyScore:
        """Compute the entropy score from raw counters.

        Parameters
        ----------
        retry_count:
            Retries consumed for the current task.
        reflection_count:
            Reflection cycles consumed for the current task.
        budget_utilization_pct:
            Current context budget utilization (0–100+).
        path_id:
            Active PATH ("A" | "B" | "C" | "D").  Unknown values are accepted;
            the advisor applies the most conservative threshold.
        """
        score = retry_count * reflection_count * budget_utilization_pct / 100.0
        return cls(
            retry_count=retry_count,
            reflection_count=reflection_count,
            budget_utilization_pct=budget_utilization_pct,
            path_id=path_id,
            score=score,
        )


# ---------------------------------------------------------------------------
# Entropy advisor
# ---------------------------------------------------------------------------


@dataclass
class DecompositionSuggestion:
    """Advisor result for a single entropy evaluation.

    Attributes
    ----------
    should_decompose:
        True when the entropy score exceeds the PATH threshold.
    reason:
        Human-readable explanation with score, threshold, and PATH info.
    entropy_score:
        Computed composite entropy value.
    threshold:
        PATH-specific threshold used for the evaluation.
    path_id:
        Active PATH at evaluation time.
    """

    should_decompose: bool
    reason: str
    entropy_score: float
    threshold: float
    path_id: str


class EntropyAdvisor:
    """Advises on task decomposition based on cognitive entropy.

    Usage example::

        advisor = EntropyAdvisor()
        suggestion = advisor.advise(
            retry_count=budget.retry_count,
            reflection_count=budget.reflection_count,
            budget_utilization_pct=pct,
            path_id="A",
        )
        if suggestion.should_decompose:
            typer.echo(suggestion.reason, err=True)
    """

    def advise(
        self,
        retry_count: int,
        reflection_count: int,
        budget_utilization_pct: float,
        path_id: str = "",
    ) -> DecompositionSuggestion:
        """Evaluate whether the current entropy warrants task decomposition.

        Returns a :class:`DecompositionSuggestion` whose ``should_decompose``
        field is ``True`` when ``entropy_score > threshold`` (strict greater-than
        — a score exactly at the threshold is still within acceptable bounds).
        """
        score = EntropyScore.compute(
            retry_count=retry_count,
            reflection_count=reflection_count,
            budget_utilization_pct=budget_utilization_pct,
            path_id=path_id,
        )
        threshold = _PATH_ENTROPY_THRESHOLD.get(path_id, _DEFAULT_ENTROPY_THRESHOLD)
        should_decompose = score.score > threshold
        path_info = f" (PATH {path_id})" if path_id else ""
        if should_decompose:
            reason = (
                f"[SDD] Entropy score {score.score:.2f} exceeds threshold "
                f"{threshold:.2f}{path_info}. "
                "Task should be decomposed into smaller PATH A/B units."
            )
        else:
            reason = (
                f"[SDD] Entropy score {score.score:.2f} within threshold "
                f"{threshold:.2f}{path_info}. No decomposition required."
            )
        return DecompositionSuggestion(
            should_decompose=should_decompose,
            reason=reason,
            entropy_score=score.score,
            threshold=threshold,
            path_id=path_id,
        )


# ---------------------------------------------------------------------------
# Convergence detection
# ---------------------------------------------------------------------------


def _compute_trend(samples: list[float]) -> float:
    """Least-squares slope of the sample series.

    Positive return value means utilization is growing (diverging);
    negative means it is shrinking (converging).
    """
    n = len(samples)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(samples) / n
    numerator = sum((i - x_mean) * (samples[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    return numerator / denominator if denominator != 0.0 else 0.0


@dataclass
class ConvergenceReport:
    """Result of a convergence assessment.

    Attributes
    ----------
    is_converging:
        True when the trend slope is within the divergence threshold.
    samples:
        The utilization percentages used in this assessment.
    trend:
        Least-squares slope (pct/step).  Positive = growing utilization.
    reason:
        Human-readable assessment message.
    """

    is_converging: bool
    samples: list[float]
    trend: float
    reason: str


class ConvergenceTracker:
    """Tracks a series of ``budget_utilization_pct`` values and detects divergence.

    Uses a sliding window of the last ``window`` observations.  When the slope
    of the window exceeds :data:`_DIVERGENCE_SLOPE_THRESHOLD` pct/step, the
    agent is consuming context faster than it is making progress.

    Parameters
    ----------
    window:
        Number of recent samples to include in slope calculation (default: 3).
    """

    def __init__(self, window: int = _CONVERGENCE_WINDOW) -> None:
        self._samples: list[float] = []
        self._window = window

    def record(self, pct: float) -> None:
        """Append a new utilization percentage observation."""
        self._samples.append(pct)

    def report(self) -> ConvergenceReport:
        """Return a convergence assessment of the current sample window."""
        window_samples = self._samples[-self._window :]
        if len(window_samples) < 2:
            return ConvergenceReport(
                is_converging=True,
                samples=list(window_samples),
                trend=0.0,
                reason="[SDD] Insufficient samples for convergence assessment.",
            )
        trend = _compute_trend(window_samples)
        is_converging = trend <= _DIVERGENCE_SLOPE_THRESHOLD
        if is_converging:
            reason = (
                f"[SDD] Utilization trend {trend:.2f}%/step ≤ threshold "
                f"{_DIVERGENCE_SLOPE_THRESHOLD:.2f}%/step. Task is converging."
            )
        else:
            reason = (
                f"[SDD] Utilization trend {trend:.2f}%/step > threshold "
                f"{_DIVERGENCE_SLOPE_THRESHOLD:.2f}%/step. "
                "Budget consumption outpacing progress — consider task decomposition."
            )
        return ConvergenceReport(
            is_converging=is_converging,
            samples=list(window_samples),
            trend=trend,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# Cross-session drift detection
# ---------------------------------------------------------------------------


@dataclass
class PathDistribution:
    """PATH classification distribution across a set of events.

    Attributes
    ----------
    counts:
        Map of path_id → event count.
    total:
        Total events with a non-empty path_id.
    dominant_path:
        The path_id with the highest count (empty string when total=0).
    is_overloaded:
        True when a "heavy" PATH (C or D) accounts for more than
        :data:`_OVERLOAD_DOMINANCE_PCT` percent of tasks.
    reason:
        Human-readable assessment message.
    """

    counts: dict[str, int]
    total: int
    dominant_path: str
    is_overloaded: bool
    reason: str


class SessionDriftScorer:
    """Detects systematic PATH overloading by analyzing event history.

    A session is considered overloaded when PATH C (complex feature) or
    PATH D (multi-thread) accounts for more than 50% of tasks across sessions —
    indicating that work is being scoped too broadly rather than decomposed.

    Usage::

        # From in-memory events
        distribution = SessionDriftScorer.from_events(sink.list_events())
        if distribution.is_overloaded:
            reason = distribution.reason

        # From JSONL audit log
        distribution = SessionDriftScorer.from_jsonl(Path(".sdd/runtime/compliance-events.jsonl"))
    """

    @staticmethod
    def from_events(events: list[Any]) -> PathDistribution:
        """Compute PATH distribution from a list of ``RuntimeEvent`` objects.

        Parameters
        ----------
        events:
            Any sequence of objects with a ``path_id`` attribute.
        """
        counts: dict[str, int] = {}
        for evt in events:
            pid = getattr(evt, "path_id", "") or ""
            if pid:
                counts[pid] = counts.get(pid, 0) + 1
        return SessionDriftScorer._make_distribution(counts)

    @staticmethod
    def from_jsonl(jsonl_path: Path) -> PathDistribution:
        """Compute PATH distribution from a JSONL compliance log file.

        Parameters
        ----------
        jsonl_path:
            Path to the JSONL audit log.  Returns an empty distribution when
            the file does not exist.
        """
        counts: dict[str, int] = {}
        if not jsonl_path.exists():
            return SessionDriftScorer._make_distribution(counts)
        with jsonl_path.open(encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    pid = data.get("path_id", "") or ""
                    if pid:
                        counts[pid] = counts.get(pid, 0) + 1
                except json.JSONDecodeError:
                    continue
        return SessionDriftScorer._make_distribution(counts)

    @staticmethod
    def _make_distribution(counts: dict[str, int]) -> PathDistribution:
        total = sum(counts.values())
        if total == 0:
            return PathDistribution(
                counts=counts,
                total=0,
                dominant_path="",
                is_overloaded=False,
                reason="[SDD] No path_id data available for drift analysis.",
            )
        dominant_path = max(counts, key=lambda k: counts[k])
        dominant_count = counts[dominant_path]
        dominant_pct = dominant_count / total * 100.0
        is_overloaded = (
            dominant_path in _HEAVY_PATHS and dominant_pct > _OVERLOAD_DOMINANCE_PCT
        )
        if is_overloaded:
            reason = (
                f"[SDD] PATH {dominant_path} dominates at {dominant_pct:.1f}% of tasks "
                f"(>{_OVERLOAD_DOMINANCE_PCT:.0f}% threshold). "
                "Systematic overloading detected — review task scoping."
            )
        else:
            reason = (
                f"[SDD] PATH distribution within bounds. "
                f"Dominant path: {dominant_path} ({dominant_pct:.1f}%)."
            )
        return PathDistribution(
            counts=counts,
            total=total,
            dominant_path=dominant_path,
            is_overloaded=is_overloaded,
            reason=reason,
        )
