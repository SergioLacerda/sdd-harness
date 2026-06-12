from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sdd_runtime import TelemetrySink
from sdd_runtime._skill_executor import SkillExecutor, _get_skill_handler
from sdd_runtime._skill_registry import SkillRegistry
from sdd_runtime.skills import _REGISTRY


def _make_executor(tmp_path: Path, sink: TelemetrySink | None = None) -> SkillExecutor:
    registry = SkillRegistry(_REGISTRY, tmp_path)
    return SkillExecutor(registry, sink)


# ---------------------------------------------------------------------------
# run_skill — missing skill / policy
# ---------------------------------------------------------------------------


def test_run_skill_returns_missing_skill(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
    result = executor.run_skill("does-not-exist")
    assert result.exit_code == 1
    assert result.policy_result == "missing_skill"
    assert result.governance_footer


def test_run_skill_warn_mode_plans_successfully(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
    with patch(
        "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
    ):
        result = executor.run_skill("sdd-review-architecture", enforcement_mode="warn")
    assert result.exit_code == 0
    assert result.policy_result == "planned"


def test_run_skill_strict_mode_blocks_high_risk(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
    with patch(
        "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
    ):
        result = executor.run_skill(
            "sdd-review-architecture", enforcement_mode="strict"
        )
    assert result.exit_code == 1
    assert result.policy_result == "blocked"


def test_run_skill_handshake_unauthorized(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
    blocked = SimpleNamespace(
        allowed=False, reason="handshake missing skill declaration"
    )
    with patch(
        "sdd_runtime.policy.PolicyEngine.evaluate_skill_policy", return_value=blocked
    ):
        result = executor.run_skill(
            "sdd-diagnose", enforcement_mode="strict", project_root=tmp_path
        )
    assert result.exit_code == 1
    assert result.policy_result == "unauthorized"


def test_run_skill_deprecated_emits_warning(tmp_path: Path) -> None:
    from sdd_runtime.skills import _REGISTRY as registry

    executor = _make_executor(tmp_path)
    original = registry["sdd-diagnose"]
    old_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    from sdd_runtime._skill_contracts import SkillDefinition

    registry["sdd-diagnose"] = SkillDefinition(
        name=original.name,
        version=original.version,
        category=original.category,
        description=original.description,
        when_to_use=list(original.when_to_use),
        outcomes=list(original.outcomes),
        allowed_tools=list(original.allowed_tools),
        cli_fallback=list(original.cli_fallback),
        required_permissions=list(original.required_permissions),
        deprecated_after=old_date,
    )
    try:
        with (
            patch(
                "sdd_runtime.policy.PolicyEngine._check_handshake_guard",
                return_value=None,
            ),
            pytest.warns(DeprecationWarning, match="is deprecated"),
        ):
            result = executor.run_skill("sdd-diagnose", project_root=tmp_path)
        assert result.exit_code == 0
    finally:
        registry["sdd-diagnose"] = original


# ---------------------------------------------------------------------------
# Footer policy
# ---------------------------------------------------------------------------


def test_run_skill_reads_footer_policy_from_runtime_state(tmp_path: Path) -> None:
    state_dir = tmp_path / ".sdd" / "runtime"
    state_dir.mkdir(parents=True)
    (state_dir / "governance-state.json").write_text(
        '{"response_footer_policy":"always"}', encoding="utf-8"
    )
    executor = _make_executor(tmp_path)
    result = executor.run_skill("sdd-diagnose", project_root=tmp_path)
    assert result.governance_footer.startswith("SDD GOVERNANCE:")


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------


def test_run_skill_emits_telemetry_on_success(tmp_path: Path) -> None:
    sink = TelemetrySink(jsonl_path=tmp_path / "events.jsonl", logging_mode="active")
    executor = _make_executor(tmp_path, sink=sink)
    executor.run_skill("sdd-diagnose")
    events = sink.list_events()
    assert events
    assert events[-1].event == "runtime.skill.run"


def test_run_skill_emits_telemetry_on_missing_skill(tmp_path: Path) -> None:
    sink = TelemetrySink(jsonl_path=tmp_path / "events.jsonl", logging_mode="active")
    executor = _make_executor(tmp_path, sink=sink)
    executor.run_skill("does-not-exist")
    events = sink.list_events()
    assert events[-1].details.get("policy_result") == "missing_skill"


# ---------------------------------------------------------------------------
# _execute_commands
# ---------------------------------------------------------------------------


def test_execute_commands_returns_empty_for_no_fallback(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
    skill = SimpleNamespace(cli_fallback=[], budget_policy={})
    code, errors, results = executor._execute_commands(skill, tmp_path)  # type: ignore[arg-type]
    assert code == 0
    assert errors == []
    assert results == []


def test_execute_commands_success(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
    skill = executor._registry.get_skill("sdd-diagnose")
    assert skill is not None

    class _FakeRunner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            return SimpleNamespace(success=True, returncode=0, stderr="")

    with (
        patch("sdd_core.utils.process.SafeProcessRunner", return_value=_FakeRunner()),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
    ):
        result = executor.run_skill("sdd-diagnose", execute=True, project_root=tmp_path)

    assert result.exit_code == 0
    assert result.policy_result == "executed"
    assert result.command_results[0]["status"] == "ok"


def test_execute_commands_failure(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)

    class _FailRunner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            return SimpleNamespace(success=False, returncode=7, stderr="boom")

    with (
        patch("sdd_core.utils.process.SafeProcessRunner", return_value=_FailRunner()),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
    ):
        result = executor.run_skill("sdd-diagnose", execute=True, project_root=tmp_path)

    assert result.exit_code == 7
    assert result.command_results[0]["exit_code"] == 7


def test_execute_commands_retries_transient_failure_then_succeeds(
    tmp_path: Path,
) -> None:
    executor = _make_executor(tmp_path)

    class _RetryRunner:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(
                    success=False, returncode=1, stderr="temporary unavailable"
                )
            return SimpleNamespace(success=True, returncode=0, stderr="")

    runner = _RetryRunner()
    with (
        patch("sdd_core.utils.process.SafeProcessRunner", return_value=runner),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
        patch("time.sleep", return_value=None),
    ):
        result = executor.run_skill("sdd-diagnose", execute=True, project_root=tmp_path)

    assert result.exit_code == 0
    assert len(result.command_results) == 3
    assert result.command_results[0]["attempt"] == 0
    assert result.command_results[1]["attempt"] == 1
    assert result.command_results[0]["retry_event"]["skill"] == "sdd-diagnose"
    assert result.command_results[2]["command"] == "sdd runtime status --force"


def test_execute_commands_does_not_retry_when_handler_default_returns_false(
    tmp_path: Path,
) -> None:
    executor = _make_executor(tmp_path)

    class _FailRunner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            return SimpleNamespace(
                success=False, returncode=1, stderr="temporary unavailable"
            )

    with (
        patch("sdd_core.utils.process.SafeProcessRunner", return_value=_FailRunner()),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
        patch("time.sleep", return_value=None),
    ):
        result = executor.run_skill(
            "sdd-stabilize", execute=True, project_root=tmp_path
        )

    assert result.exit_code == 1
    assert len(result.command_results) == 1


def test_execute_commands_timeout_maps_to_124(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)

    class _TimeoutRunner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            from sdd_core.utils.process import ProcessTimeoutError

            raise ProcessTimeoutError(cmd=args, timeout=1.0)

    with (
        patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=_TimeoutRunner()
        ),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
    ):
        result = executor.run_skill("sdd-diagnose", execute=True, project_root=tmp_path)

    assert result.exit_code == 124
    assert result.policy_result == "timeout"
    assert result.command_results[0]["error"] == "timeout"
    assert result.artifacts["timeout_event"]["skill"] == "sdd-diagnose"


def test_execute_commands_retries_timeout_until_limit(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)

    class _TimeoutRunner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            from sdd_core.utils.process import ProcessTimeoutError

            raise ProcessTimeoutError(cmd=args, timeout=1.0)

    with (
        patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=_TimeoutRunner()
        ),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
        patch("time.sleep", return_value=None),
    ):
        result = executor.run_skill("sdd-diagnose", execute=True, project_root=tmp_path)

    assert result.exit_code == 124
    assert len(result.command_results) == 2
    assert result.command_results[-1]["attempt"] == 1


def test_timeout_hook_records_failure_in_learning_ledger(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)

    class _TimeoutRunner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            from sdd_core.utils.process import ProcessTimeoutError

            raise ProcessTimeoutError(cmd=args, timeout=1.0)

    with (
        patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=_TimeoutRunner()
        ),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
        patch("time.sleep", return_value=None),
    ):
        executor.run_skill("sdd-diagnose", execute=True, project_root=tmp_path)

    ledger = (tmp_path / ".sdd" / "runtime" / "failure-ledger.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"symptom": "timeout"' in ledger


def test_retry_hook_records_retry_in_learning_ledger(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)

    class _RetryRunner:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(
                    success=False, returncode=1, stderr="temporary unavailable"
                )
            return SimpleNamespace(success=True, returncode=0, stderr="")

    with (
        patch("sdd_core.utils.process.SafeProcessRunner", return_value=_RetryRunner()),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
        patch("time.sleep", return_value=None),
    ):
        executor.run_skill("sdd-diagnose", execute=True, project_root=tmp_path)

    ledger = (tmp_path / ".sdd" / "runtime" / "failure-ledger.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"symptom": "retry"' in ledger


def test_pipeline_escalates_on_stage_timeout(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)

    class _TimeoutRunner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            from sdd_core.utils.process import ProcessTimeoutError

            raise ProcessTimeoutError(cmd=args, timeout=1.0)

    with (
        patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=_TimeoutRunner()
        ),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
        patch("time.sleep", return_value=None),
    ):
        result = executor.run_skill("sdd-pipeline", execute=True, project_root=tmp_path)

    assert result.exit_code == 124
    assert result.policy_result == "escalated"
    assert result.reason == "stage_timeout:sdd-ask"
    assert result.artifacts["pipeline_timeout"]["trigger_stage"] == "sdd-ask"


def test_pipeline_logs_stage_timeout(tmp_path: Path, caplog) -> None:
    executor = _make_executor(tmp_path)

    class _TimeoutRunner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            from sdd_core.utils.process import ProcessTimeoutError

            raise ProcessTimeoutError(cmd=args, timeout=1.0)

    with (
        patch(
            "sdd_core.utils.process.SafeProcessRunner", return_value=_TimeoutRunner()
        ),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
        patch("time.sleep", return_value=None),
        caplog.at_level("WARNING"),
    ):
        executor.run_skill("sdd-pipeline", execute=True, project_root=tmp_path)

    assert "Pipeline stage timeout" in caplog.text


def test_execute_commands_runner_init_failure(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
    with (
        patch("sdd_core.utils.process.SafeProcessRunner", side_effect=RuntimeError),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
    ):
        result = executor.run_skill("sdd-diagnose", execute=True, project_root=tmp_path)

    assert result.exit_code == 1
    assert result.command_results[0]["status"] == "error"


# ---------------------------------------------------------------------------
# Handler factory (re-tested at executor level)
# ---------------------------------------------------------------------------


def test_get_skill_handler_returns_none_for_unknown() -> None:
    assert _get_skill_handler("sdd-stabilize").__class__.__name__ == "StabilizeHandler"
    assert _get_skill_handler("diagnose") is None


def test_get_skill_handler_returns_pipeline_handler() -> None:
    assert _get_skill_handler("sdd-pipeline").__class__.__name__ == "PipelineHandler"


def test_get_skill_handler_returns_compress_context_handler() -> None:
    assert (
        _get_skill_handler("sdd-compress-context").__class__.__name__
        == "CompressContextHandler"
    )


def test_get_skill_handler_returns_review_architecture_handler() -> None:
    assert (
        _get_skill_handler("sdd-review-architecture").__class__.__name__
        == "ReviewArchitectureHandler"
    )


def test_get_skill_handler_returns_stabilize_handler() -> None:
    assert _get_skill_handler("sdd-stabilize").__class__.__name__ == "StabilizeHandler"


def test_run_skill_pipeline_composes_stage_artifacts(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
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
        result = executor.run_skill(
            "sdd-pipeline", context=context, project_root=tmp_path
        )

    assert result.exit_code == 0
    assert result.policy_result == "planned"
    assert result.artifacts["gate_decision"]["decision"] == "allow"
    assert result.artifacts["pipeline_state"]["completed_stages"] == [
        "sdd-ask",
        "sdd-diagnose",
        "sdd-correct",
        "sdd-converge",
    ]


def test_run_skill_compress_context_returns_summary_artifacts(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
    context = {
        "governance_fingerprint": "abc123",
        "chat_log": "z" * 240,
    }

    with patch(
        "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
    ):
        result = executor.run_skill(
            "sdd-compress-context", context=context, project_root=tmp_path
        )

    assert result.exit_code == 0
    assert result.artifacts["compressed_context"]["governance_fingerprint"] == "abc123"
    assert result.artifacts["compressed_context"]["chat_log"]["type"] == "string"


def test_run_skill_review_architecture_returns_review_artifacts(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
    context = {
        "governance_score": 70,
        "baseline_governance_score": 85,
        "architecture_violations": ["M001", "M010"],
        "baseline_architecture_violations": ["M001"],
    }

    with patch(
        "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
    ):
        result = executor.run_skill(
            "sdd-review-architecture", context=context, project_root=tmp_path
        )

    assert result.exit_code == 0
    assert result.artifacts["architecture_deltas"]["added_violations"] == ["M010"]
    assert result.artifacts["governance_score"] == 70


def test_run_skill_stabilize_returns_stabilization_report(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)

    class _MixedRunner:
        def run(self, args, cwd=None, capture_output=False, timeout=120):  # noqa: ANN001
            command = " ".join(args)
            if "test" in command:
                return SimpleNamespace(success=False, returncode=2, stderr="boom")
            return SimpleNamespace(success=True, returncode=0, stderr="")

    with (
        patch("sdd_core.utils.process.SafeProcessRunner", return_value=_MixedRunner()),
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
    ):
        result = executor.run_skill(
            "sdd-stabilize", execute=True, project_root=tmp_path
        )

    assert result.exit_code == 2
    assert result.artifacts["stabilization_report"]["decision"] == "block"
    assert result.artifacts["stabilization_report"]["test_failures"] == [
        "sdd test ci-validate"
    ]


def test_run_skill_pipeline_returns_stage_escalation(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)

    with patch(
        "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
    ):
        result = executor.run_skill("sdd-pipeline", project_root=tmp_path)

    assert result.exit_code == 1
    assert result.policy_result == "escalated"
    assert result.artifacts["pipeline_state"]["completed_stages"] == [
        "sdd-ask",
        "sdd-diagnose",
    ]
    assert result.artifacts["pipeline_gate_decision"]["decision"] == "skip_and_escalate"
    assert result.artifacts["pipeline_gate_decision"]["reason_code"] == (
        "diagnosis.inconclusive"
    )


def test_run_skill_pipeline_escalates_on_freeze_mode(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
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
        result = executor.run_skill(
            "sdd-pipeline", context=context, project_root=tmp_path
        )

    assert result.exit_code == 2
    assert result.policy_result == "escalated"
    assert result.artifacts["pipeline_escalation"]["reason"] == (
        "convergence.freeze_mode_active"
    )


def test_run_skill_pipeline_logs_freeze_escalation(tmp_path: Path, caplog) -> None:
    executor = _make_executor(tmp_path)
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

    with (
        patch(
            "sdd_runtime.policy.PolicyEngine._check_handshake_guard", return_value=None
        ),
        caplog.at_level("CRITICAL"),
    ):
        executor.run_skill("sdd-pipeline", context=context, project_root=tmp_path)

    assert "Pipeline freeze escalation triggered" in caplog.text


def test_run_skill_pipeline_uses_custom_confidence_threshold(tmp_path: Path) -> None:
    executor = _make_executor(tmp_path)
    context = {
        "pipeline_min_diagnosis_confidence": 0.5,
        "execution_contract": {
            "allowed_paths": ["safe/path"],
            "task_id": "task-3",
            "min_diagnosis_confidence": 0.5,
        },
        "diagnosis_report": {
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.6,
        },
        "diagnosis_attestation": {
            "task_id": "task-3",
            "hypothesis": "h",
            "root_cause": "r",
            "evidence_refs": ["e"],
            "confidence": 0.6,
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
        result = executor.run_skill(
            "sdd-pipeline", context=context, project_root=tmp_path
        )

    assert result.exit_code == 0
    assert result.artifacts["pipeline_state"]["completed_stages"] == [
        "sdd-ask",
        "sdd-diagnose",
        "sdd-correct",
        "sdd-converge",
    ]
