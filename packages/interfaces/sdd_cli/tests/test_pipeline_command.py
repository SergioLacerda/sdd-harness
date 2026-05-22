from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner
from sdd_runtime._skill_executor import _evaluate_correction_gate

from sdd_cli.main import app

runner = CliRunner()


def _load_json_output(raw: str) -> dict:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return json.loads(lines[-1])


def _payload_data(payload: dict) -> dict:
    value = payload.get("data")
    return value if isinstance(value, dict) else payload


def test_pipeline_run_json_happy_path(tmp_path) -> None:
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
        result = runner.invoke(app, ["--json", "pipeline", "fix runtime bug"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "ok"
    assert payload["command"] == "pipeline"
    assert payload["ok"] is True
    assert payload["error"] is None
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "pipeline_completed"
    assert data["final_gate_decision"]["decision"] == "allow"
    assert "ask_decision_envelope" in data["pipeline"]["ask"]
    assert "diagnosis_attestation" in data["pipeline"]["diagnose"]


def test_pipeline_run_json_blocked_returns_exit_one(tmp_path) -> None:
    diagnose = SimpleNamespace(
        artifacts={
            "diagnosis_report": {},
            "diagnosis_attestation": {},
        },
        command_results=[],
    )
    correct = SimpleNamespace(
        artifacts={
            "gate_decision": {
                "decision": "deny",
                "reason_code": "convergence.freeze_mode_active",
                "next_action": "run-converge-and-human-review",
                "requires_human_review": True,
            }
        },
        command_results=[],
    )
    converge = SimpleNamespace(
        artifacts={
            "convergence_delta_report": {},
            "freeze_mode_state": {"enabled": True},
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
        result = runner.invoke(app, ["--json", "pipeline", "fix runtime bug"])
    assert result.exit_code == 1, result.output
    payload = _load_json_output(result.output)
    assert payload["status"] == "error"
    assert payload["command"] == "pipeline"
    assert payload["ok"] is False
    assert isinstance(payload["error"], dict)
    assert isinstance(payload["data"], dict)
    data = _payload_data(payload)
    assert data["policy_result"] == "pipeline_blocked"
    assert (
        data["final_gate_decision"]["reason_code"] == "convergence.freeze_mode_active"
    )


def test_pipeline_run_denies_when_contract_expired(tmp_path) -> None:
    stale_envelope = {
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
        "issued_at": "2000-01-01T00:00:00+00:00",
        "expires_at": "2000-01-01T00:30:00+00:00",
    }

    def _run_skill_side_effect(name: str, **kwargs):
        context = kwargs.get("context", {})
        if name == "sdd-diagnose":
            return SimpleNamespace(
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
        if name == "sdd-correct":
            gate = _evaluate_correction_gate(context, active_rules=[])
            return SimpleNamespace(
                artifacts={"gate_decision": gate}, command_results=[]
            )
        return SimpleNamespace(
            artifacts={
                "convergence_delta_report": {},
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
                "ask_decision_envelope": stale_envelope,
            },
        ),
        patch(
            "sdd_cli.commands.pipeline.SkillEngine.run_skill",
            side_effect=_run_skill_side_effect,
        ),
    ):
        result = runner.invoke(app, ["--json", "pipeline", "fix runtime bug"])
    assert result.exit_code == 1, result.output
    payload = _load_json_output(result.output)
    data = _payload_data(payload)
    assert data["final_gate_decision"]["reason_code"] == "contract.missing_or_invalid"


def test_pipeline_run_denies_when_attestation_expired(tmp_path) -> None:
    def _run_skill_side_effect(name: str, **kwargs):
        context = kwargs.get("context", {})
        if name == "sdd-diagnose":
            return SimpleNamespace(
                artifacts={
                    "diagnosis_report": {
                        "hypothesis": "h",
                        "root_cause": "r",
                        "evidence_refs": ["e1"],
                        "confidence": 0.9,
                    },
                    "diagnosis_attestation": {
                        "task_id": context["execution_contract"]["task_id"],
                        "hypothesis": "h",
                        "root_cause": "r",
                        "evidence_refs": ["e1"],
                        "confidence": 0.9,
                        "issued_at": "2000-01-01T00:00:00+00:00",
                        "expires_at": "2000-01-01T00:01:00+00:00",
                    },
                },
                command_results=[],
            )
        if name == "sdd-correct":
            gate = _evaluate_correction_gate(context, active_rules=[])
            return SimpleNamespace(
                artifacts={"gate_decision": gate}, command_results=[]
            )
        return SimpleNamespace(
            artifacts={
                "convergence_delta_report": {},
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
                    "task_type": "correct",
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
            side_effect=_run_skill_side_effect,
        ),
    ):
        result = runner.invoke(
            app,
            ["--json", "pipeline", "--skill", "correct", "fix runtime bug"],
        )
    assert result.exit_code == 1, result.output
    payload = _load_json_output(result.output)
    data = _payload_data(payload)
    assert data["final_gate_decision"]["reason_code"] == "diagnosis.stale"


def test_pipeline_json_contract_snapshot_shape(tmp_path) -> None:
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
        result = runner.invoke(app, ["--json", "pipeline", "fix runtime bug"])
    assert result.exit_code == 0, result.output
    payload = _load_json_output(result.output)

    assert set(payload.keys()) >= {"status", "command", "ok", "error", "data"}
    data = _payload_data(payload)
    assert set(data["pipeline"].keys()) == {"ask", "diagnose", "correct", "converge"}
    assert set(data["pipeline"]["ask"].keys()) == {
        "ask_decision_envelope",
        "learning_context",
        "learning_recommendations",
    }
    assert set(data["pipeline"]["diagnose"].keys()) == {
        "diagnosis_report",
        "diagnosis_attestation",
    }
    assert set(data["pipeline"]["correct"].keys()) == {
        "gate_decision",
        "command_results",
        "artifacts",
    }
    assert set(data["pipeline"]["converge"].keys()) == {
        "convergence_delta_report",
        "freeze_mode_state",
    }


def test_pipeline_run_exits_3_on_permission_error(tmp_path) -> None:
    with (
        runner.isolated_filesystem(temp_dir=str(tmp_path)),
        patch(
            "sdd_cli.commands.pipeline.build_governed_ask_snapshot",
            side_effect=PermissionError("governance handshake required"),
        ),
    ):
        result = runner.invoke(app, ["pipeline", "fix bug"])
    assert result.exit_code == 3


def test_pipeline_run_exits_2_on_zero_budget(tmp_path) -> None:
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
                    "goal": "fix bug",
                    "allowed_paths": [],
                    "forbidden_paths": [],
                    "allowed_tools": [],
                    "validation_set": [],
                    "rollback_hint": "",
                    "requires_diagnosis": True,
                    "envelope_scope_mode": "inferred",
                    "min_diagnosis_confidence": 0.8,
                    "issued_at": "2099-01-01T00:00:00+00:00",
                    "expires_at": "2099-01-01T00:30:00+00:00",
                },
            },
        ),
    ):
        result = runner.invoke(app, ["pipeline", "--budget", "0", "fix bug"])
    assert result.exit_code == 2


class TestLoadFreezeModeState:
    def test_returns_disabled_when_file_missing(self, tmp_path) -> None:
        from sdd_cli.commands.pipeline import _load_freeze_mode_state

        result = _load_freeze_mode_state(tmp_path, task_id="t1")
        assert result == {"enabled": False}

    def test_returns_disabled_on_json_decode_error(self, tmp_path) -> None:
        from sdd_cli.commands.pipeline import _load_freeze_mode_state

        state_file = tmp_path / ".sdd" / "runtime" / "freeze-mode-state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("not-json", encoding="utf-8")
        result = _load_freeze_mode_state(tmp_path, task_id="t1")
        assert result == {"enabled": False}

    def test_returns_disabled_when_payload_not_dict(self, tmp_path) -> None:
        import json

        from sdd_cli.commands.pipeline import _load_freeze_mode_state

        state_file = tmp_path / ".sdd" / "runtime" / "freeze-mode-state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        result = _load_freeze_mode_state(tmp_path, task_id="t1")
        assert result == {"enabled": False}

    def test_returns_disabled_when_task_id_mismatch(self, tmp_path) -> None:
        import json

        from sdd_cli.commands.pipeline import _load_freeze_mode_state

        state_file = tmp_path / ".sdd" / "runtime" / "freeze-mode-state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(
            json.dumps({"enabled": True, "task_id": "other"}), encoding="utf-8"
        )
        result = _load_freeze_mode_state(tmp_path, task_id="mine")
        assert result["enabled"] is False

    def test_sets_default_task_id_when_absent(self, tmp_path) -> None:
        import json

        from sdd_cli.commands.pipeline import _load_freeze_mode_state

        state_file = tmp_path / ".sdd" / "runtime" / "freeze-mode-state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"enabled": True}), encoding="utf-8")
        result = _load_freeze_mode_state(tmp_path, task_id="mine")
        assert result["task_id"] == "mine"


def test_pipeline_ignores_freeze_state_from_different_task_id(tmp_path) -> None:
    runtime_dir = tmp_path / ".sdd" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "freeze-mode-state.json").write_text(
        json.dumps({"enabled": True, "task_id": "other-task"}), encoding="utf-8"
    )
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
    captured_correct_context: dict = {}

    def _run_skill(name: str, **kwargs):
        nonlocal captured_correct_context
        if name == "sdd-diagnose":
            return diagnose
        if name == "sdd-correct":
            captured_correct_context = kwargs.get("context", {})
            return SimpleNamespace(
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
        return SimpleNamespace(
            artifacts={
                "convergence_delta_report": {},
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
            "sdd_cli.commands.pipeline.SkillEngine.run_skill", side_effect=_run_skill
        ),
    ):
        result = runner.invoke(app, ["--json", "pipeline", "fix runtime bug"])
    assert result.exit_code == 0, result.output
    assert captured_correct_context["freeze_mode_state"]["enabled"] is False
