"""Integration tests for sdd audit (summary) CLI command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from sdd_cli.main import app

runner = CliRunner()


def _write_events(path: Path) -> None:
    events = [
        {
            "event": "governance.ask",
            "command": "ask",
            "status": "ok",
            "start_ts": "2026-05-20T10:00:00Z",
            "artifact_fingerprint": "aaaaaaaa11111111",
            "tokens_input": 120,
            "tokens_output": 60,
            "details": {"drift_detected": False},
        },
        {
            "event": "runtime.drift.detected",
            "command": "runtime status",
            "status": "warn",
            "start_ts": "2026-05-20T10:05:00Z",
            "artifact_fingerprint": "bbbbbbbb22222222",
            "details": {
                "drift_type": "profile_drift",
                "reason": "profile mismatch",
                "remediation_command": "sdd runtime status --force",
            },
        },
        {
            "event": "governance.ask",
            "command": "ask",
            "status": "warn",
            "start_ts": "2026-05-20T10:10:00Z",
            "artifact_fingerprint": "cccccccc33333333",
            "tokens_input": 80,
            "tokens_output": 40,
            "details": {"drift_detected": True, "drift_type": "session_drift"},
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for item in events:
            fh.write(json.dumps(item) + "\n")


def test_audit_default_output(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(app, ["audit", "--events-file", str(events_file)])
    assert result.exit_code == 0, result.output
    assert "SDD Audit Summary" in result.output
    assert "- total events: 3" in result.output
    assert "- total drifts: 2" in result.output
    assert "Correlation Windows (7/14/30)" in result.output
    assert "Top 10 Drift Events" in result.output
    assert "profile_drift" in result.output


def test_audit_json_output(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(app, ["--json", "audit", "--events-file", str(events_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert payload["command"] == "audit"
    assert payload["ok"] is True
    assert payload["data"]["total_events"] == 3
    assert payload["data"]["total_drifts"] == 2
    assert payload["data"]["token_comparison"]["total_input_tokens"] == 200
    assert payload["data"]["token_comparison"]["total_output_tokens"] == 100
    assert "drift_unclassified_total" in payload["data"]
    assert "correlation_windows" in payload["data"]
    assert [w["window_days"] for w in payload["data"]["correlation_windows"]] == [
        7,
        14,
        30,
    ]
    assert len(payload["data"]["top_drifts"]) == 2


def test_audit_json_output_uses_canonical_data_payload(
    tmp_path: Path, monkeypatch
) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(app, ["--json", "audit", "--events-file", str(events_file)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert payload["command"] == "audit"
    assert payload["data"]["total_events"] == 3
    assert "total_events" not in payload


def test_audit_include_non_drift_flag(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_events(events_file)
    result = runner.invoke(
        app,
        ["--json", "audit", "--events-file", str(events_file), "--include-non-drift"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert "non_drift_events" in payload["data"]


def test_audit_no_drift_events_text_output(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    events_file.parent.mkdir(parents=True, exist_ok=True)
    events_file.write_text(
        json.dumps(
            {
                "event": "governance.ask",
                "command": "ask",
                "start_ts": "2026-05-20T10:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["audit", "--events-file", str(events_file)])
    assert result.exit_code == 0
    assert "no drift events found" in result.output
