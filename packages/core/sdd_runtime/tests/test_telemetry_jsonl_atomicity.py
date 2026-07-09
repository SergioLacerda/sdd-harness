"""Atomicity/durability guards for TelemetrySink JSONL append (A6).

Regression coverage for the risk noted in the initial critique: concurrent
writers appending to the same compliance-events.jsonl segment could
interleave partial lines, and a crash right after emit() could lose an event
that only ever reached the OS page cache. `_write_jsonl` now takes an
exclusive advisory lock around the write and fsyncs before returning.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sdd_runtime import RuntimeEvent, TelemetrySink
from sdd_runtime.telemetry import MODE_ACTIVE


def _make_event(event_name: str) -> RuntimeEvent:
    return RuntimeEvent(event=event_name, command="runtime", status="ok", trace_id="t1")


def test_write_jsonl_locks_and_fsyncs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Every append takes an exclusive flock and calls os.fsync before releasing it."""
    calls: list[str] = []

    import sdd_runtime.telemetry._sink as sink_module

    class _FakeFcntl:
        LOCK_EX = 2
        LOCK_UN = 8

        @staticmethod
        def flock(fd: int, op: int) -> None:
            calls.append(f"flock:{op}")

    real_fsync = sink_module.os.fsync

    def _tracking_fsync(fd: int) -> None:
        calls.append("fsync")
        real_fsync(fd)

    monkeypatch.setattr(sink_module, "fcntl", _FakeFcntl)
    monkeypatch.setattr(sink_module.os, "fsync", _tracking_fsync)

    jsonl_path = tmp_path / "compliance-events.jsonl"
    sink = TelemetrySink(jsonl_path=jsonl_path, logging_mode=MODE_ACTIVE)
    sink.emit(_make_event("runtime.session.start"))

    assert calls == [f"flock:{_FakeFcntl.LOCK_EX}", "fsync"]
    assert jsonl_path.read_text(encoding="utf-8").strip()


def test_write_jsonl_releases_lock_even_when_fsync_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A failed fsync must not leave the file handle (and its flock) dangling."""
    import sdd_runtime.telemetry._sink as sink_module

    calls: list[str] = []

    class _FakeFcntl:
        LOCK_EX = 2
        LOCK_UN = 8

        @staticmethod
        def flock(fd: int, op: int) -> None:
            calls.append(f"flock:{op}")

    def _raising_fsync(fd: int) -> None:
        raise OSError("simulated disk full")

    monkeypatch.setattr(sink_module, "fcntl", _FakeFcntl)
    monkeypatch.setattr(sink_module.os, "fsync", _raising_fsync)

    jsonl_path = tmp_path / "compliance-events.jsonl"
    sink = TelemetrySink(jsonl_path=jsonl_path, logging_mode=MODE_ACTIVE)

    with pytest.raises(OSError, match="simulated disk full"):
        sink.emit(_make_event("runtime.session.start"))

    # The file handle closes (context manager exit) even though fsync raised,
    # so a second writer can still acquire the lock afterwards.
    monkeypatch.setattr(sink_module.os, "fsync", lambda fd: None)
    sink.emit(_make_event("runtime.session.start"))
    assert jsonl_path.read_text(encoding="utf-8").strip()
