"""Thread-safe collector state, reload worker, and path helpers for metrics commands."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from sdd_runtime.metrics import EconomySnapshot

_RUNTIME_DIR = Path(".sdd") / "runtime"
_EVENTS_FILENAME = "compliance-events.jsonl"


class _CollectorRef:
    """Thread-safe mutable reference to the active collector."""

    def __init__(self, collector: object) -> None:
        self._lock = threading.RLock()
        self._collector = collector

    def swap(self, collector: object) -> None:
        with self._lock:
            self._collector = collector

    def snapshot(self) -> EconomySnapshot:
        with self._lock:
            return cast("EconomySnapshot", self._collector.snapshot())  # type: ignore[attr-defined]


def _start_reload_worker(
    *,
    jsonl_path: Path,
    refresh: int,
    collector_ref: _CollectorRef,
    stop_event: threading.Event,
) -> threading.Thread:
    """Start periodic collector reload worker with deterministic shutdown."""
    from sdd_runtime.metrics import TokenEconomyCollector
    from sdd_runtime.reader import TelemetryReader

    def reload_collector() -> None:
        while not stop_event.is_set():
            # Wait with cancellation support instead of sleep(refresh)
            if stop_event.wait(refresh):
                break
            try:
                reader = TelemetryReader(jsonl_path)
                new_collector = TokenEconomyCollector.from_reader(reader)
                collector_ref.swap(new_collector)
            except Exception:  # nosec B110
                # Silently ignore reload errors; keep previous collector active
                pass

    worker = threading.Thread(
        target=reload_collector,
        name="sdd-metrics-reloader",
        # Preserve daemon semantics of caller thread for test harness compatibility.
        daemon=threading.current_thread().daemon,
    )
    worker.start()
    return worker


def _resolve_jsonl_path(jsonl: Path | None) -> Path:
    """Resolve the JSONL events file path.

    Priority:
    1. Explicit --jsonl argument
    2. {cwd}/.sdd/runtime/compliance-events.jsonl
    3. Fallback to just the filename (for testing)
    """
    if jsonl:
        return jsonl

    default = _RUNTIME_DIR / _EVENTS_FILENAME
    return default
