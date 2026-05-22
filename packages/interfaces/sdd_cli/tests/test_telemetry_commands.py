"""Tests for sdd telemetry init/status/dump/query commands per observability-core plan."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from sdd_cli.main import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sink(tmp_path: Path, events: list[dict]) -> Path:
    runtime_dir = tmp_path / ".sdd" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    sink = runtime_dir / "compliance-events.jsonl"
    sink.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return sink


def _patch_root(monkeypatch, tmp_path: Path) -> None:
    # Force workspace-based sink resolution inside tests even if outer
    # environments export telemetry path overrides (e.g. CI container jobs).
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    monkeypatch.setattr(
        "sdd_cli.commands.telemetry.resolve_workspace_root", lambda: tmp_path
    )


# ---------------------------------------------------------------------------
# sdd telemetry init
# ---------------------------------------------------------------------------


def test_init_creates_directory_and_file(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    result = runner.invoke(app, ["--json", "telemetry", "init"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["created"] is True
    assert payload["data"]["valid"] is True
    assert Path(os.path.realpath(payload["data"]["events_file"])).exists()


def test_init_idempotent(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    runner.invoke(app, ["--json", "telemetry", "init"])
    result = runner.invoke(app, ["--json", "telemetry", "init"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["created"] is False
    assert payload["data"]["valid"] is True


def test_init_validates_corrupt_jsonl(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    sink = tmp_path / ".sdd" / "runtime" / "compliance-events.jsonl"
    sink.parent.mkdir(parents=True, exist_ok=True)
    sink.write_text('{"event": "ok"}\nNOT JSON\n{"event": "ok"}\n', encoding="utf-8")
    result = runner.invoke(app, ["--json", "telemetry", "init"])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_jsonl"
    assert payload["data"]["invalid_line"] == 2


def test_init_skips_blank_lines(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    sink = tmp_path / ".sdd" / "runtime" / "compliance-events.jsonl"
    sink.parent.mkdir(parents=True, exist_ok=True)
    sink.write_text('{"event": "ok"}\n\n{"event": "ok2"}\n', encoding="utf-8")
    result = runner.invoke(app, ["--json", "telemetry", "init"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["valid"] is True


# ---------------------------------------------------------------------------
# sdd telemetry status
# ---------------------------------------------------------------------------


def test_status_missing_file_includes_hint(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    result = runner.invoke(app, ["--json", "telemetry", "status"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["total_events"] == 0
    assert "hint" in payload["data"]
    assert "init" in payload["data"]["hint"]


def test_status_empty_file_no_hint(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(app, ["--json", "telemetry", "status"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["total_events"] == 0
    assert "hint" not in payload["data"]


def test_status_event_type_breakdown(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "governance.ask", "status": "ok"},
            {"event": "governance.ask", "status": "ok"},
            {"event": "runtime.drift.detected", "status": "warn"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "status"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["total_events"] == 3
    assert payload["data"]["events_by_type"]["governance.ask"] == 2
    assert payload["data"]["events_by_type"]["runtime.drift.detected"] == 1


# ---------------------------------------------------------------------------
# sdd telemetry dump
# ---------------------------------------------------------------------------


def test_dump_trace_id_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "governance.ask", "trace_id": "abc123"},
            {"event": "governance.ask", "trace_id": "def456"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "dump", "--trace-id", "abc123"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["returned"] == 1
    assert payload["data"]["events"][0]["trace_id"] == "abc123"


def test_dump_format_json_array(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": "e1"}, {"event": "e2"}])
    result = runner.invoke(app, ["telemetry", "dump", "--format", "json"])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert len(parsed) == 2


def test_dump_limit(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": f"e{i}"} for i in range(10)])
    result = runner.invoke(app, ["--json", "telemetry", "dump", "--limit", "3"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["returned"] == 3


def test_dump_invalid_format_errors(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": "e1"}])
    result = runner.invoke(app, ["--json", "telemetry", "dump", "--format", "yaml"])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_format"


# ---------------------------------------------------------------------------
# sdd telemetry query — new filters
# ---------------------------------------------------------------------------


def test_query_trace_id_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "e1", "trace_id": "aaa", "start_ts": "2026-05-21T10:00:00Z"},
            {"event": "e2", "trace_id": "bbb", "start_ts": "2026-05-21T10:01:00Z"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "query", "--trace-id", "aaa"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["matched"] == 1
    assert payload["data"]["events"][0]["trace_id"] == "aaa"


def test_query_status_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "e1", "status": "ok"},
            {"event": "e2", "status": "fail"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "query", "--status", "ok"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["matched"] == 1


def test_query_level_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "e1", "level": "ERROR"},
            {"event": "e2", "level": "INFO"},
        ],
    )
    result = runner.invoke(app, ["--json", "telemetry", "query", "--level", "ERROR"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["matched"] == 1


def test_query_until_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "early", "start_ts": "2026-05-01T00:00:00Z"},
            {"event": "late", "start_ts": "2026-05-21T00:00:00Z"},
        ],
    )
    result = runner.invoke(
        app, ["--json", "telemetry", "query", "--until", "2026-05-10T00:00:00Z"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["matched"] == 1
    assert payload["data"]["events"][0]["event"] == "early"


def test_query_invalid_until_errors(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(
        app, ["--json", "telemetry", "query", "--until", "not-a-date"]
    )
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_until"


def test_query_and_semantics_all_filters(monkeypatch, tmp_path: Path) -> None:
    """All filters are AND — event must satisfy every filter provided."""
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "governance.ask", "status": "ok", "trace_id": "aaa"},
            {"event": "governance.ask", "status": "fail", "trace_id": "bbb"},
            {"event": "runtime.drift", "status": "ok", "trace_id": "aaa"},
        ],
    )
    result = runner.invoke(
        app,
        [
            "--json",
            "telemetry",
            "query",
            "--event-type",
            "governance.ask",
            "--status",
            "ok",
            "--trace-id",
            "aaa",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["data"]["matched"] == 1


def test_query_no_results_returns_empty_list(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": "governance.ask", "trace_id": "xyz"}])
    result = runner.invoke(
        app, ["--json", "telemetry", "query", "--trace-id", "nonexistent"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["matched"] == 0
    assert payload["data"]["events"] == []


# ---------------------------------------------------------------------------
# Plain-text (non-JSON) output paths — coverage for human-readable branches
# ---------------------------------------------------------------------------


def test_status_text_output_with_events(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {
                "event": "governance.ask",
                "status": "ok",
                "start_ts": "2026-05-21T10:00:00Z",
            },
            {
                "event": "governance.ask",
                "status": "ok",
                "start_ts": "2026-05-21T10:01:00Z",
            },
        ],
    )
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    assert "Total events: 2" in result.output
    assert "governance.ask" in result.output


def test_status_text_missing_file_shows_hint(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    assert "init" in result.output.lower()


def test_status_text_empty_file(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    assert "No events" in result.output


def test_dump_text_jsonl_output(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": "e1"}, {"event": "e2"}])
    result = runner.invoke(app, ["telemetry", "dump", "--limit", "10"])
    assert result.exit_code == 0
    lines = [line for line in result.output.strip().splitlines() if line]
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "e1"


def test_query_text_output_with_results(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "governance.ask", "start_ts": "2026-05-21T10:00:00Z"},
        ],
    )
    result = runner.invoke(
        app, ["telemetry", "query", "--event-type", "governance.ask"]
    )
    assert result.exit_code == 0
    assert "governance.ask" in result.output
    assert "1 events matched" in result.output


def test_query_text_since_invalid_non_json(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(app, ["telemetry", "query", "--since", "bad-date"])
    assert result.exit_code == 1
    assert "Invalid --since" in result.output


def test_query_text_until_invalid_non_json(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [])
    result = runner.invoke(app, ["telemetry", "query", "--until", "bad-date"])
    assert result.exit_code == 1
    assert "Invalid --until" in result.output


def test_query_work_item_filter(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    _make_sink(
        tmp_path,
        [
            {"event": "e1", "work_item_id": "ticket-123"},
            {"event": "e2", "work_item_id": "ticket-456"},
        ],
    )
    result = runner.invoke(
        app, ["--json", "telemetry", "query", "--work-item", "ticket-123"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["data"]["matched"] == 1


def test_init_text_creates_file(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    result = runner.invoke(app, ["telemetry", "init"])
    assert result.exit_code == 0
    assert "Created" in result.output


def test_init_text_already_exists(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    runner.invoke(app, ["telemetry", "init"])
    result = runner.invoke(app, ["telemetry", "init"])
    assert result.exit_code == 0
    assert "Already exists" in result.output


def test_init_text_invalid_jsonl(monkeypatch, tmp_path: Path) -> None:
    _patch_root(monkeypatch, tmp_path)
    sink = tmp_path / ".sdd" / "runtime" / "compliance-events.jsonl"
    sink.parent.mkdir(parents=True, exist_ok=True)
    sink.write_text('{"ok": true}\nBAD JSON\n', encoding="utf-8")
    result = runner.invoke(app, ["telemetry", "init"])
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_default_events_path_fallback_on_exception(monkeypatch) -> None:
    """_default_events_path raises when resolve_workspace_root fails."""
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    monkeypatch.setattr(
        "sdd_cli.commands.telemetry.resolve_workspace_root",
        lambda: (_ for _ in ()).throw(RuntimeError("no workspace")),
    )
    from sdd_cli.commands.telemetry import _default_events_path

    with pytest.raises(RuntimeError):
        _default_events_path()


def test_status_workspace_resolution_failure_json(monkeypatch) -> None:
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    monkeypatch.setattr(
        "sdd_cli.commands.telemetry.resolve_workspace_root",
        lambda: (_ for _ in ()).throw(RuntimeError("no workspace")),
    )
    result = runner.invoke(app, ["--json", "telemetry", "status"])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "workspace_resolution_failed"


def test_status_workspace_resolution_failure_text(monkeypatch) -> None:
    monkeypatch.delenv("SDD_TELEMETRY_PATH", raising=False)
    monkeypatch.setattr(
        "sdd_cli.commands.telemetry.resolve_workspace_root",
        lambda: (_ for _ in ()).throw(RuntimeError("no workspace")),
    )
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 1
    assert "failed to resolve workspace root" in result.output


def test_parse_ts_empty_string_returns_none() -> None:
    from sdd_cli.commands.telemetry import _parse_ts

    assert _parse_ts("") is None


def test_telemetry_default_callback_invokes_status(monkeypatch, tmp_path: Path) -> None:
    """sdd telemetry (no subcommand) calls _print_status."""
    _patch_root(monkeypatch, tmp_path)
    _make_sink(tmp_path, [{"event": "governance.ask", "status": "ok"}])
    result = runner.invoke(app, ["telemetry"])
    assert result.exit_code == 0
    assert "governance.ask" in result.output or "Total" in result.output
