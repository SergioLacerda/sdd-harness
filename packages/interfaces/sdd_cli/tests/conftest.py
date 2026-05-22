"""Shared fixtures for sdd_cli tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sdd_runtime import RuntimeEvent


@pytest.fixture
def metrics_events_path(tmp_path: Path) -> Path:
    """Fixture that provides isolated JSONL path with synthetic metrics events.

    Events are written to tmp_path/generated/metrics-events.jsonl to avoid
    reading from production .sdd/runtime/ directory.
    """
    events_path = tmp_path / "generated" / "metrics-events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)

    # Write synthetic events for testing
    events = [
        # Session startup events
        RuntimeEvent(
            event="runtime.session.start",
            command="runtime status",
            status="ok",
            trace_id="trace-synthetic-1",
            workspace_id="ws-test",
            agent_id="agent-test",
            artifact_fingerprint="fp-test",
            schema_version="3.0",
        ),
        # Token consumption events (required for TokenEconomyCollector aggregation)
        RuntimeEvent(
            event="economy.token.consume",
            command="ask",
            status="ok",
            trace_id="trace-synthetic-2",
            workspace_id="ws-test",
            agent_id="agent-test",
            artifact_fingerprint="fp-test",
            schema_version="3.0",
            tokens_input=100,
            tokens_output=50,
            tokens_total=150,
            details={"model": "claude-test", "cost_usd": 0.0012},
        ),
        RuntimeEvent(
            event="economy.token.consume",
            command="ask",
            status="ok",
            trace_id="trace-synthetic-3",
            workspace_id="ws-test",
            agent_id="agent-test",
            artifact_fingerprint="fp-test",
            schema_version="3.0",
            tokens_input=200,
            tokens_output=100,
            tokens_total=300,
            details={"model": "claude-test", "cost_usd": 0.0024},
        ),
        RuntimeEvent(
            event="economy.token.consume",
            command="ask",
            status="ok",
            trace_id="trace-synthetic-4",
            workspace_id="ws-test",
            agent_id="agent-test",
            artifact_fingerprint="fp-test",
            schema_version="3.0",
            tokens_input=150,
            tokens_output=75,
            tokens_total=225,
            details={"model": "claude-test", "cost_usd": 0.0018},
        ),
    ]

    with events_path.open("w", encoding="utf-8") as fh:
        for evt in events:
            fh.write(evt.to_json() + "\n")

    return events_path
