from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from sdd_runtime._skill_executor import SkillExecutor, _get_skill_handler
from sdd_runtime._skill_registry import SkillRegistry
from sdd_runtime.skills import _REGISTRY


def _make_executor(tmp_path: Path) -> SkillExecutor:
    return SkillExecutor(SkillRegistry(_REGISTRY, tmp_path))


def test_get_skill_handler_contract_still_resolves_known_handlers() -> None:
    assert _get_skill_handler("sdd-pipeline").__class__.__name__ == "PipelineHandler"
    assert _get_skill_handler("diagnose") is None


def test_run_skill_pipeline_composes_stage_artifacts(tmp_path: Path) -> None:
    context = {
        "execution_contract": {"allowed_paths": ["safe/path"], "task_id": "task-1"},
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.95,
        },
        "diagnosis_attestation": {
            "task_id": "task-1",
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.95,
            "issued_at": "2099-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T01:00:00+00:00",
        },
        "planned_paths": ["safe/path"],
        "convergence_delta_report": {
            "alignment_score": 0.95,
            "residual_violations": [],
        },
    }
    with patch(
        "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-pipeline", context=context, project_root=tmp_path
        )
    assert result.exit_code == 0
    assert result.artifacts["pipeline_state"]["completed_stages"] == [
        "sdd-ask",
        "sdd-diagnose",
        "sdd-correct",
        "sdd-converge",
    ]


def test_run_skill_pipeline_returns_stage_escalation(tmp_path: Path) -> None:
    with patch(
        "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-pipeline", project_root=tmp_path
        )
    assert result.exit_code == 1
    assert result.policy_result == "escalated"
    assert result.artifacts["pipeline_gate_decision"]["decision"] == "skip_and_escalate"


def test_run_skill_pipeline_escalates_on_freeze_mode(tmp_path: Path) -> None:
    context = {
        "execution_contract": {"allowed_paths": ["safe/path"], "task_id": "task-2"},
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.95,
        },
        "diagnosis_attestation": {
            "task_id": "task-2",
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.95,
            "issued_at": "2099-01-01T00:00:00+00:00",
            "expires_at": "2099-01-01T01:00:00+00:00",
        },
        "planned_paths": ["safe/path"],
        "convergence_delta_report": {"alignment_score": 0.1, "residual_violations": []},
    }
    with patch(
        "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-pipeline", context=context, project_root=tmp_path
        )
    assert result.exit_code == 2
    assert (
        result.artifacts["pipeline_escalation"]["reason"]
        == "convergence.freeze_mode_active"
    )
