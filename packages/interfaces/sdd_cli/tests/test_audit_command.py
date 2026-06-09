"""Integration tests for sdd audit CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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


def _write_view_events(path: Path) -> None:
    events = [
        {
            "event": "VIOLATION",
            "command": "ask",
            "status": "warn",
            "start_ts": "2025-05-30T09:00:00Z",
            "artifact_fingerprint": "aaaabbbbccccdddd",
            "details": {"drift_type": "policy_drift"},
        },
        {
            "event": "VIOLATION",
            "command": "ask",
            "status": "warn",
            "start_ts": "2025-06-15T09:00:00Z",
            "artifact_fingerprint": "eeeeffff11112222",
            "details": {"drift_type": "session_drift"},
            "tokens_input": 21,
            "tokens_output": 13,
        },
        {
            "event": "INFO",
            "command": "runtime status",
            "status": "ok",
            "start_ts": "2025-06-15T10:00:00Z",
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


def test_audit_view_filters_by_since_and_event_type(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_view_events(events_file)
    result = runner.invoke(
        app,
        [
            "audit",
            "view",
            "--events-file",
            str(events_file),
            "--since",
            "2025-06-01",
            "--event-type",
            "VIOLATION",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "matched events: 1" in result.output
    assert "ask" in result.output
    assert "runtime status" not in result.output


def test_audit_export_csv_and_manifest(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    manifest_file = tmp_path / "manifest.json"
    _write_view_events(events_file)
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--events-file",
            str(events_file),
            "--since",
            "2025-06-01",
            "--event-type",
            "VIOLATION",
            "--format",
            "csv",
            "--manifest-file",
            str(manifest_file),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (
        "timestamp,event,command,status,drift_type,cause,artifact_fingerprint,tokens_input,tokens_output"
        in result.output
    )
    assert "VIOLATION,ask,warn,session_drift" in result.output
    assert manifest_file.exists()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest["format"] == "csv"
    assert manifest["count"] == 1
    assert manifest["filters"]["since"] == "2025-06-01"
    assert manifest["filters"]["event_type"] == "VIOLATION"
    assert len(manifest["sha256"]) == 64


def test_audit_export_rejects_unknown_format(tmp_path: Path) -> None:
    events_file = tmp_path / "events.jsonl"
    _write_view_events(events_file)
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--events-file",
            str(events_file),
            "--format",
            "json",
        ],
    )
    assert result.exit_code != 0
    assert "Only --format=csv is currently supported." in result.output


def test_audit_legacy_check_blocks_in_q4_with_hits(tmp_path: Path) -> None:
    legacy_doc = tmp_path / "README.md"
    legacy_doc.write_text("use /legacy/path here", encoding="utf-8")
    with patch("sdd_cli.commands.audit.resolve_workspace_root", return_value=tmp_path):
        result = runner.invoke(
            app,
            ["audit", "legacy-check", "--phase-date", "2026-10-01"],
        )
    assert result.exit_code == 2
    assert "policy mode: block" in result.output


def test_audit_bootstrap_check_ok(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "Initial reference: .sdd/agent-instructions.md\nClaude: ./CLAUDE.md\n",
        encoding="utf-8",
    )
    (tmp_path / "CLAUDE.md").write_text(
        "Read .sdd/agent-instructions.md", encoding="utf-8"
    )
    with patch("sdd_cli.commands.audit.resolve_workspace_root", return_value=tmp_path):
        result = runner.invoke(app, ["audit", "bootstrap-check"])
    assert result.exit_code == 0, result.output
    assert "status: OK" in result.output


def test_audit_compliance_pack_generates_files(tmp_path: Path) -> None:
    events_file = tmp_path / ".sdd" / "runtime" / "compliance-events.jsonl"
    _write_view_events(events_file)
    out_dir = tmp_path / "pack"

    with (
        patch("sdd_cli.commands.audit.resolve_workspace_root", return_value=tmp_path),
        patch(
            "sdd_cli.commands.audit.SafeProcessRunner.run",
            side_effect=[
                SimpleNamespace(stdout="runtime ok\n", stderr="", returncode=0),
                SimpleNamespace(stdout="governance ok\n", stderr="", returncode=0),
            ],
        ),
    ):
        result = runner.invoke(
            app,
            [
                "audit",
                "compliance-pack",
                "--out-dir",
                str(out_dir),
                "--since",
                "2025-06-01",
                "--event-type",
                "VIOLATION",
            ],
        )

    assert result.exit_code == 0, result.output
    assert (out_dir / "compliance_report.csv").exists()
    assert (out_dir / "compliance_report.manifest.json").exists()
    assert (out_dir / "runtime_status.txt").exists()
    assert (out_dir / "governance_validation.txt").exists()
    assert (out_dir / "decision_trace.md").exists()
    assert (out_dir / "external_review_checklist.md").exists()
