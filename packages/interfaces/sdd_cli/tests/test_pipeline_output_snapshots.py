from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from sdd_cli.main import app
from tests.helpers.text_io import read_text_utf8

runner = CliRunner()
SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _load_json_output(raw: str) -> dict:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _normalize_pipeline_payload(payload: dict) -> dict:
    normalized = json.loads(json.dumps(payload))
    if "trace_id" in normalized:
        normalized["trace_id"] = "__TRACE_ID__"
    if isinstance(normalized.get("data"), dict) and "trace_id" in normalized["data"]:
        normalized["data"]["trace_id"] = "__TRACE_ID__"
    return normalized


def _assert_json_snapshot(name: str, payload: dict) -> None:
    expected = json.loads(read_text_utf8(SNAPSHOT_DIR / name))
    assert _normalize_pipeline_payload(payload) == expected


def test_pipeline_run_json_snapshot(tmp_path) -> None:
    diagnose = SimpleNamespace(
        artifacts={
            "diagnosis_report": {
                "hypothesis": "h",
                "root_cause": "r",
                "evidence_refs": ["e1"],
                "confidence": 0.9,
            },
            "diagnosis_attestation": {
                "task_id": "task-1",
                "hypothesis": "h",
                "root_cause": "r",
                "evidence_refs": ["e1"],
                "confidence": 0.9,
                "issued_at": "2099-01-01T00:00:00+00:00",
                "expires_at": "2099-01-01T01:00:00+00:00",
            },
        },
        command_results=[],
    )
    correct = SimpleNamespace(
        artifacts={
            "gate_decision": {
                "decision": "allow",
                "reason_code": "ok",
                "next_action": "apply-correction",
                "requires_human_review": False,
            }
        },
        command_results=[],
    )
    converge = SimpleNamespace(
        artifacts={
            "convergence_delta_report": {
                "alignment_score": 0.95,
                "residual_violations": [],
                "next_targets": [],
            },
            "freeze_mode_state": {"enabled": False},
        },
        command_results=[],
    )
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "sdd_cli.commands.pipeline.build_governed_ask_snapshot",
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
                    "goal": "fix runtime bug",
                    "allowed_paths": ["safe/"],
                    "forbidden_paths": [],
                    "allowed_tools": ["sdd ask"],
                    "validation_set": ["sdd governance validate"],
                    "rollback_hint": "manual_rollback",
                    "requires_diagnosis": True,
                    "envelope_scope_mode": "inferred",
                    "min_diagnosis_confidence": 0.8,
                    "issued_at": "2099-01-01T00:00:00+00:00",
                    "expires_at": "2099-01-01T00:30:00+00:00",
                },
            },
        ),
        patch(
            "sdd_cli.commands.pipeline.SkillEngine.run_skill",
            side_effect=[diagnose, correct, converge],
        ),
    ):
        result = runner.invoke(
            app,
            ["--json", "pipeline", "fix runtime bug"],
            env={"SDD_ENFORCE_PIPELINE_CORRECT": "1"},
        )
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    _assert_json_snapshot("pipeline_run.json", payload)
