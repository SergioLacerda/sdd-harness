"""Ask phase-latency collector — aggregates governance.ask.phase events.

Kept separate from TokenEconomyCollector per the trace-route design's
"Recommended Ownership" decision: governance latency and token/budget/retry
economy are distinct metric domains.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..reader import TelemetryReader
    from ..telemetry import RuntimeEvent


@dataclass(frozen=True)
class LatencyGroup:
    """Aggregated latency statistics for one (phase_id, latency_domain, path_id) group."""

    count: int
    min_ms: int
    max_ms: int
    avg_ms: float
    p50_ms: int
    p95_ms: int


@dataclass(frozen=True)
class AskLatencySnapshot:
    """Point-in-time snapshot of aggregated ask-phase latency metrics.

    Thread-safe snapshot captured from AskLatencyCollector.snapshot().
    Keyed by (phase_id, latency_domain, path_id).
    """

    groups: dict[tuple[str, str, str], LatencyGroup] = field(default_factory=dict)


def _percentile(sorted_values: list[int], pct: float) -> int:
    """Compute the ``pct``-th percentile via linear interpolation between closest ranks.

    This is the "linear interpolation between closest ranks" method (matching
    numpy's default ``np.percentile`` behavior): the rank ``k`` is computed as
    ``(n - 1) * pct / 100`` (zero-indexed), and when ``k`` falls between two
    integer indices, the result is a weighted average of the values at the
    floor and ceiling ranks, weighted by how close ``k`` is to each.

    Worked examples (hand-verified):
      values = [10, 20, 30, 40, 100] (n=5, already sorted)
        p50: k = (5-1)*0.50 = 2.0 -> exact index 2 -> 30
        p95: k = (5-1)*0.95 = 3.8 -> f=3 (40), c=4 (100)
              -> 40*(4-3.8) + 100*(3.8-3) = 40*0.2 + 100*0.8 = 8 + 80 = 88
      values = [10, 20, 30, 40] (n=4, already sorted)
        p50: k = (4-1)*0.50 = 1.5 -> f=1 (20), c=2 (30)
              -> 20*(2-1.5) + 30*(1.5-1) = 10 + 15 = 25
    """
    if not sorted_values:
        return 0
    k = (len(sorted_values) - 1) * (pct / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    lower = sorted_values[f] * (c - k)
    upper = sorted_values[c] * (k - f)
    return round(lower + upper)


class AskLatencyCollector:
    """Aggregates `governance.ask.phase` events by (phase_id, latency_domain, path_id).

    Thread-safe; uses a single RLock for all mutations. Can be populated from
    a TelemetryReader (JSONL replay) or by calling ingest(event) on each live
    RuntimeEvent.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._durations: dict[tuple[str, str, str], list[int]] = {}

    def ingest(self, event: RuntimeEvent | dict[str, Any]) -> None:
        """Update internal duration lists from a single RuntimeEvent or dict.

        No-op on irrelevant event types or events missing ``duration_ms``.
        Acquires lock for all mutations.

        Parameters
        ----------
        event:
            A RuntimeEvent or dict representation (e.g., from JSONL). Must have
            fields: event, duration_ms, path_id, details (dict with phase_id /
            latency_domain).
        """
        event_dict = event.to_dict() if hasattr(event, "to_dict") else event

        if event_dict.get("event") != "governance.ask.phase":
            return

        duration_ms = event_dict.get("duration_ms")
        if duration_ms is None:
            return

        details = event_dict.get("details") or {}
        phase_id = details.get("phase_id", "unknown")
        latency_domain = details.get("latency_domain", "unknown")
        path_id = event_dict.get("path_id") or "unknown"

        key = (phase_id, latency_domain, path_id)
        with self._lock:
            self._durations.setdefault(key, []).append(int(duration_ms))

    @classmethod
    def from_reader(cls, reader: TelemetryReader) -> AskLatencyCollector:
        """Build a collector by replaying all governance.ask.phase events from a TelemetryReader.

        Parameters
        ----------
        reader:
            An initialized TelemetryReader pointing to a JSONL events file.

        Returns
        -------
        AskLatencyCollector with aggregated state from all matching events.
        """
        collector = cls()
        for evt in reader.list_events():
            collector.ingest(evt)
        return collector

    def snapshot(self) -> AskLatencySnapshot:
        """Return a copy of the current aggregated state.

        Thread-safe; acquires lock for the entire copy operation.

        Returns
        -------
        AskLatencySnapshot with point-in-time values. Safe to share/serialize.
        """
        with self._lock:
            groups: dict[tuple[str, str, str], LatencyGroup] = {}
            for key, values in self._durations.items():
                sorted_values = sorted(values)
                groups[key] = LatencyGroup(
                    count=len(sorted_values),
                    min_ms=sorted_values[0],
                    max_ms=sorted_values[-1],
                    avg_ms=sum(sorted_values) / len(sorted_values),
                    p50_ms=_percentile(sorted_values, 50),
                    p95_ms=_percentile(sorted_values, 95),
                )
            return AskLatencySnapshot(groups=groups)

    def reset(self) -> None:
        """Reset all accumulated durations."""
        with self._lock:
            self._durations.clear()
