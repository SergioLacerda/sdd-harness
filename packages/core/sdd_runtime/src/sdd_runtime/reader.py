"""TelemetryReader — Query interface for runtime events (Phase 1 implementation).

Provides local ad-hoc queries over JSONL event files without requiring Python REPL.
Supports filtering by event type, time window, status, and aggregation of token economy.

Usage::

    from sdd_runtime.reader import TelemetryReader
    from pathlib import Path

    reader = TelemetryReader(Path(".sdd/runtime/events.jsonl"))

    # Get recent events of a specific type
    events = reader.get_events_by_type("economy.token.consume", last_hours=24)

    # Token consumption summary
    summary = reader.get_token_stats()

    # Error rate analysis
    error_rate = reader.get_error_rate()

    # Budget status
    budget = reader.get_budget_status()
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass
class TokenStats:
    """Summary of token consumption across events."""

    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    event_count: int = 0
    unique_models: set[str] = None  # type: ignore
    cost_usd: float = 0.0
    avg_tokens_per_event: float = 0.0

    def __post_init__(self) -> None:
        if self.unique_models is None:
            self.unique_models = set()

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return {
            "total_tokens": self.total_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "event_count": self.event_count,
            "unique_models": sorted(self.unique_models),
            "cost_usd": round(self.cost_usd, 4),
            "avg_tokens_per_event": round(self.avg_tokens_per_event, 1),
        }


@dataclass
class BudgetStatus:
    """Current budget utilization snapshot."""

    max_tokens: int = 0
    consumed_tokens: int = 0
    utilization_pct: float = 0.0
    max_cost_usd: float | None = None
    consumed_cost_usd: float = 0.0
    warning_threshold_pct: float = 90.0
    breach_threshold_pct: float = 100.0
    in_red_zone: bool = False
    in_breach: bool = False

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return {
            "max_tokens": self.max_tokens,
            "consumed_tokens": self.consumed_tokens,
            "utilization_pct": self.utilization_pct,
            "max_cost_usd": self.max_cost_usd,
            "consumed_cost_usd": round(self.consumed_cost_usd, 4),
            "warning_threshold_pct": self.warning_threshold_pct,
            "breach_threshold_pct": self.breach_threshold_pct,
            "in_red_zone": self.in_red_zone,
            "in_breach": self.in_breach,
        }


class TelemetryReader:
    """Local query interface for runtime event JSONL files.

    Phase 1 implementation provides basic filtering, aggregation, and summaries.
    All operations are in-memory; suitable for single-session analysis.

    Parameters
    ----------
    jsonl_path:
        Path to the JSONL event file (e.g., ``.sdd/runtime/events.jsonl``).
        If the file does not exist, operations return empty results gracefully.
    """

    def __init__(self, jsonl_path: Path) -> None:
        self._path = jsonl_path
        self._events: list[dict[str, Any]] = []
        self._load_events()

    def _load_events(self) -> None:
        """Load all events from the JSONL file into memory."""
        if not self._path.exists():
            return

        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            self._events.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue
        except Exception:  # nosec B110
            # Gracefully handle read errors
            pass

    def get_events_by_type(
        self, event_type: str, last_hours: int | None = None
    ) -> list[dict[str, Any]]:
        """Get events of a specific type, optionally filtered by time window.

        Parameters
        ----------
        event_type:
            Event type to filter by (e.g., "economy.token.consume").
        last_hours:
            If provided, only return events from the last N hours.

        Returns
        -------
        List of matching events (empty if none found).
        """
        matching = [e for e in self._events if e.get("event") == event_type]

        if last_hours is None:
            return matching

        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=last_hours)
        filtered = []
        for event in matching:
            try:
                ts_str = event.get("ts", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts >= cutoff:
                        filtered.append(event)
            except ValueError:
                # Skip events with unparseable timestamps
                continue
        return filtered

    def get_token_stats(self, last_hours: int | None = None) -> TokenStats:
        """Aggregate token consumption statistics across all economy.token.consume events.

        Parameters
        ----------
        last_hours:
            If provided, only analyze events from the last N hours.

        Returns
        -------
        TokenStats object with aggregated totals and summaries.
        """
        events = self.get_events_by_type("economy.token.consume", last_hours)

        stats = TokenStats()
        for event in events:
            tokens_input = event.get("tokens_input") or 0
            tokens_output = event.get("tokens_output") or 0
            tokens_total = event.get("tokens_total") or 0

            stats.total_input_tokens += tokens_input
            stats.total_output_tokens += tokens_output
            stats.total_tokens += tokens_total
            stats.event_count += 1

            # Extract model from details
            details = event.get("details", {})
            if isinstance(details, dict):
                model = details.get("model", "unknown")
                stats.unique_models.add(model)
                cost = details.get("cost_usd", 0.0)
                stats.cost_usd += cost

        if stats.event_count > 0:
            stats.avg_tokens_per_event = stats.total_tokens / stats.event_count

        return stats

    def get_error_rate(self, last_hours: int | None = None) -> dict[str, Any]:
        """Compute error rate across all events.

        Parameters
        ----------
        last_hours:
            If provided, only analyze events from the last N hours.

        Returns
        -------
        Dict with error statistics: {total_events, error_events, error_rate, error_types}.
        """
        if last_hours is not None:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=last_hours)
            events = []
            for event in self._events:
                try:
                    ts_str = event.get("ts", "")
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts >= cutoff:
                            events.append(event)
                except ValueError:
                    continue
        else:
            events = self._events

        total = len(events)
        if total == 0:
            return {
                "total_events": 0,
                "error_events": 0,
                "error_rate": 0.0,
                "error_types": {},
            }

        error_events = [e for e in events if e.get("status") == "fail"]
        error_count = len(error_events)

        # Aggregate error types
        error_types: dict[str, int] = {}
        for event in error_events:
            event_type = event.get("event", "unknown")
            error_types[event_type] = error_types.get(event_type, 0) + 1

        return {
            "total_events": total,
            "error_events": error_count,
            "error_rate": round(error_count / total * 100, 2) if total > 0 else 0.0,
            "error_types": error_types,
        }

    def get_budget_status(self) -> BudgetStatus:
        """Get current budget status from the most recent economy.budget.* events.

        Returns
        -------
        BudgetStatus snapshot based on latest available data.
        """
        status = BudgetStatus()

        # Find the most recent budget event
        budget_events = [
            e for e in self._events if e.get("event", "").startswith("economy.budget")
        ]

        if not budget_events:
            return status

        # Use the most recent event
        latest = budget_events[-1]
        details = latest.get("details", {})

        if isinstance(details, dict):
            status.consumed_tokens = details.get("consumed", 0)
            status.max_tokens = details.get("limit", 0)
            status.consumed_cost_usd = details.get("consumed", 0.0)
            status.max_cost_usd = details.get("limit")

            if status.max_tokens > 0:
                status.utilization_pct = round(
                    (status.consumed_tokens / status.max_tokens) * 100, 2
                )

            status.in_red_zone = status.utilization_pct >= status.warning_threshold_pct
            status.in_breach = status.utilization_pct >= status.breach_threshold_pct

        return status

    def get_events_by_agent(self, agent_id: str) -> list[dict[str, Any]]:
        """Get all events from a specific agent.

        Parameters
        ----------
        agent_id:
            Agent ID to filter by.

        Returns
        -------
        List of events from the specified agent.
        """
        return [e for e in self._events if e.get("agent_id") == agent_id]

    def get_events_by_status(self, status: str) -> list[dict[str, Any]]:
        """Get all events with a specific status (ok, warn, fail).

        Parameters
        ----------
        status:
            Status value to filter by (ok, warn, fail).

        Returns
        -------
        List of events with the specified status.
        """
        return [e for e in self._events if e.get("status") == status]

    def get_latest_events(self, n: int = 50) -> list[dict[str, Any]]:
        """Get the N most recent events.

        Parameters
        ----------
        n:
            Number of recent events to return.

        Returns
        -------
        List of the N most recent events (empty if fewer than N exist).
        """
        return self._events[-n:] if self._events else []

    def get_event_count(self) -> int:
        """Return total count of loaded events."""
        return len(self._events)

    def list_events(self) -> list[dict[str, Any]]:
        """Return all loaded events as a list of dicts.

        Returns
        -------
        All events from the JSONL file (empty list if file does not exist).
        """
        return list(self._events)

    def clear_cache(self) -> None:
        """Reload events from disk (useful if file was updated externally)."""
        self._events = []
        self._load_events()
