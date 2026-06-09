"""Pure event reading, parsing, and filtering functions for telemetry commands."""

from __future__ import annotations

import contextlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                with contextlib.suppress(json.JSONDecodeError):
                    events.append(json.loads(stripped))
    return events


def _event_ts(event: dict[str, Any]) -> str:
    for key in ("end_ts", "start_ts", "ts", "timestamp"):
        value = str(event.get(key, "")).strip()
        if value:
            return value
    return ""


def _parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def filter_events(
    events: list[dict[str, Any]],
    *,
    event_type: str | None = None,
    status_filter: str | None = None,
    level: str | None = None,
    trace_id: str | None = None,
    work_item: str | None = None,
) -> list[dict[str, Any]]:
    """Apply field-equality filters to an events list (all filters are AND)."""
    if event_type:
        events = [
            e for e in events if str(e.get("event", "")).lower() == event_type.lower()
        ]
    if status_filter:
        events = [
            e
            for e in events
            if str(e.get("status", "")).lower() == status_filter.lower()
        ]
    if level:
        events = [e for e in events if str(e.get("level", "")).upper() == level.upper()]
    if trace_id:
        events = [e for e in events if str(e.get("trace_id", "")) == trace_id]
    if work_item:
        events = [
            e
            for e in events
            if str(e.get("work_item_id", "")).lower() == work_item.lower()
        ]
    return events


def apply_time_filter(
    events: list[dict[str, Any]],
    since_str: str | None,
    until_str: str | None,
) -> tuple[list[dict[str, Any]], str | None, str | None]:
    """Apply since/until time filters.

    Returns (filtered_events, since_error, until_error) where each error is the
    invalid input string if parsing failed, or None if the filter was valid/absent.
    """
    if since_str:
        since_dt = _parse_ts(since_str)
        if since_dt is None:
            return events, since_str, None
        events = [
            e
            for e in events
            if (ts := _event_ts(e))
            and (dt := _parse_ts(ts)) is not None
            and dt >= since_dt
        ]

    if until_str:
        until_dt = _parse_ts(until_str)
        if until_dt is None:
            return events, None, until_str
        events = [
            e
            for e in events
            if (ts := _event_ts(e))
            and (dt := _parse_ts(ts)) is not None
            and dt <= until_dt
        ]

    return events, None, None
