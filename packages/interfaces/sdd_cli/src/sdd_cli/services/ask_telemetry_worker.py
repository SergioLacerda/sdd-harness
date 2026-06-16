"""Async telemetry flush worker and canonical event routing for ask command flows."""

from __future__ import annotations

import atexit
import json
import queue
import threading
from collections.abc import Callable
from contextlib import suppress
from typing import Any, Protocol

from sdd_runtime import RuntimeEvent

from sdd_core.output.canonical_event import CanonicalLogEvent, ProfileRenderer

_TELEMETRY_LEVELS = ("debug", "trace")


class _EventSink(Protocol):
    def emit(self, event: RuntimeEvent) -> None:
        pass


def route_canonical_event(
    event: CanonicalLogEvent, *, renderer: ProfileRenderer | None = None
) -> str:
    """Route a canonical event per M020.

    `level=debug` and `level=trace` events always emit structured JSON via
    `to_telemetry_dict()`, bypassing the profile renderer. Other levels are
    rendered through `ProfileRenderer.render()` (compact `simple_output()`).
    """
    if event.level in _TELEMETRY_LEVELS:
        return json.dumps(event.to_telemetry_dict())
    return (renderer or ProfileRenderer()).render(event)


_TELEMETRY_QUEUE: queue.Queue[Callable[[], None] | None] = queue.Queue()


def _telemetry_worker() -> None:
    while True:
        callback = _TELEMETRY_QUEUE.get()
        if callback is None:
            break
        with suppress(Exception):
            callback()


_TELEMETRY_WORKER = threading.Thread(target=_telemetry_worker, daemon=True)
_TELEMETRY_WORKER.start()


def _shutdown_telemetry_worker() -> None:
    _TELEMETRY_QUEUE.put(None)
    _TELEMETRY_WORKER.join(timeout=2)


atexit.register(_shutdown_telemetry_worker)


def enqueue_flush(sink: Any) -> None:
    """Flush telemetry asynchronously when the sink exposes a flush method."""
    flush = getattr(sink, "flush", None)
    if callable(flush):
        _TELEMETRY_QUEUE.put(flush)
