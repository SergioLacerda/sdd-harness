from __future__ import annotations

from pathlib import Path

from sdd_runtime import TelemetrySink
from sdd_runtime._skill_executor._executor_results import build_execution_result
from sdd_runtime._skill_executor._executor_telemetry import emit_skill_telemetry


def test_emit_skill_telemetry_writes_runtime_event(tmp_path: Path) -> None:
    sink = TelemetrySink(jsonl_path=tmp_path / "events.jsonl", logging_mode="active")
    emit_skill_telemetry(
        sink,
        build_execution_result(
            skill_name="sdd-diagnose",
            profile="default",
            policy_result="planned",
            reason="ok",
            exit_code=0,
            governance_footer="",
            fallback=[],
            command_results=[],
            artifacts={},
        ),
    )
    assert sink.list_events()[-1].event == "runtime.skill.run"


def test_emit_skill_telemetry_noops_without_sink() -> None:
    emit_skill_telemetry(
        None,
        build_execution_result(
            skill_name="sdd-diagnose",
            profile="default",
            policy_result="planned",
            reason="ok",
            exit_code=0,
            governance_footer="",
            fallback=[],
            command_results=[],
            artifacts={},
        ),
    )
