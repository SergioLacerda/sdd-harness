from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from sdd_cli.main import app
from tests.helpers.text_io import read_text_utf8

runner = CliRunner()
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _load_json_output(raw: str) -> dict:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _normalize_ask_payload(payload: dict) -> dict:
    normalized = json.loads(json.dumps(payload))
    # ask --json does not include trace_id, but envelope task_id/timestamps are dynamic.
    envelope = normalized.get("data", {}).get("ask_decision_envelope", {})
    if isinstance(envelope, dict):
        if "task_id" in envelope:
            envelope["task_id"] = "__TASK_ID__"
        if "issued_at" in envelope:
            envelope["issued_at"] = "__ISSUED_AT__"
        if "expires_at" in envelope:
            envelope["expires_at"] = "__EXPIRES_AT__"
    return normalized


def _assert_json_snapshot(name: str, payload: dict) -> None:
    expected = json.loads(read_text_utf8(SNAPSHOT_DIR / name))
    assert _normalize_ask_payload(payload) == expected


def test_ask_run_json_snapshot(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "sdd_cli.commands._ask_backend._resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "sdd_cli.commands._ask_backend._run_organize_intake",
            return_value=(False, "light", "", 0, "indexed_only"),
        ),
        patch(
            "sdd_cli.commands._ask_backend._get_profile_state",
            return_value=("master", "HEALTHY"),
        ),
        patch("sdd_cli.commands._ask_backend._emit_ask_telemetry", return_value=None),
        patch("sdd_cli.commands._ask_backend._write_runtime_cache", return_value=None),
        patch("sdd_cli.commands._ask_backend._upsert_ask_session", return_value=None),
        patch(
            "sdd_cli.commands._ask_backend.build_governed_ask_snapshot",
            return_value={
                "workspace_root": tmp_path,
                "context_source": "compiled",
                "fingerprint": "fp-1",
                "mandates_count": 1,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "verified",
                "drift_detected": False,
                "learning_recommendation": None,
                "learning_context": {
                    "window_days": 7,
                    "observed_events": 0,
                    "recommendation_policy_version": "ask-learning-v1",
                },
                "ask_decision_envelope": {
                    "task_id": "task-1",
                    "task_type": "analysis",
                    "goal": "status?",
                    "allowed_paths": [],
                    "forbidden_paths": [],
                    "allowed_tools": [
                        "sdd ask",
                        "sdd skills run sdd-diagnose",
                        "sdd skills run sdd-correct",
                    ],
                    "validation_set": [
                        "sdd governance validate",
                        "sdd runtime status --force",
                    ],
                    "rollback_hint": "manual_rollback",
                    "requires_diagnosis": True,
                    "envelope_scope_mode": "inferred",
                    "min_diagnosis_confidence": 0.8,
                    "issued_at": "2099-01-01T00:00:00+00:00",
                    "expires_at": "2099-01-01T00:30:00+00:00",
                },
            },
        ),
    ):
        result = runner.invoke(app, ["--json", "ask", "status?"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    _assert_json_snapshot("ask_run.json", payload)


def test_ask_run_json_with_learning_snapshot(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "sdd_cli.commands._ask_backend._resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "sdd_cli.commands._ask_backend._run_organize_intake",
            return_value=(False, "light", "", 0, "indexed_only"),
        ),
        patch(
            "sdd_cli.commands._ask_backend._get_profile_state",
            return_value=("master", "HEALTHY"),
        ),
        patch("sdd_cli.commands._ask_backend._emit_ask_telemetry", return_value=None),
        patch("sdd_cli.commands._ask_backend._write_runtime_cache", return_value=None),
        patch("sdd_cli.commands._ask_backend._upsert_ask_session", return_value=None),
        patch(
            "sdd_cli.commands._ask_backend.build_governed_ask_snapshot",
            return_value={
                "workspace_root": tmp_path,
                "context_source": "compiled",
                "fingerprint": "fp-1",
                "mandates_count": 1,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "verified",
                "drift_detected": False,
                "learning_recommendation": {
                    "enabled": True,
                    "confidence": 0.6667,
                    "signals": ["diagnosis_inconclusive_recurrent"],
                    "reason_codes": ["diagnosis.inconclusive.recurrent"],
                    "next_actions": [
                        "sdd skills learning-candidates",
                        "sdd skills learning-status --window-days 7",
                    ],
                    "requires_human_review": True,
                },
                "learning_context": {
                    "window_days": 7,
                    "observed_events": 2,
                    "recommendation_policy_version": "ask-learning-v1",
                },
                "ask_decision_envelope": {
                    "task_id": "task-1",
                    "task_type": "analysis",
                    "goal": "status?",
                    "allowed_paths": [],
                    "forbidden_paths": [],
                    "allowed_tools": [
                        "sdd ask",
                        "sdd skills run sdd-diagnose",
                        "sdd skills run sdd-correct",
                    ],
                    "validation_set": [
                        "sdd governance validate",
                        "sdd runtime status --force",
                    ],
                    "rollback_hint": "manual_rollback",
                    "requires_diagnosis": True,
                    "envelope_scope_mode": "inferred",
                    "min_diagnosis_confidence": 0.8,
                    "issued_at": "2099-01-01T00:00:00+00:00",
                    "expires_at": "2099-01-01T00:30:00+00:00",
                },
            },
        ),
    ):
        result = runner.invoke(app, ["--json", "ask", "status?"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    _assert_json_snapshot("ask_run_with_learning.json", payload)
