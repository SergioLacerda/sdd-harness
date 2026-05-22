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
    assert result.command_results[0]["error"] == "timeout"


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
    assert _get_skill_handler("sdd-stabilize") is None
    assert _get_skill_handler("diagnose") is None
