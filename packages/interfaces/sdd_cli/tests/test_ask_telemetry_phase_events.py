"""Tests for governance.ask.phase child event emission and trace linkage.

Pattern mirrors `test_ask_telemetry_emit.py` (FakeSink capturing real
`RuntimeEvent` objects via a patched `TelemetrySink`) combined with
`test_ask_telemetry_path_id.py` / `test_ask_telemetry_integration.py`
(driving the real `ask_cmd` entrypoint with the surrounding
guard/organize/snapshot/profile helpers mocked out).

Unlike the path_id/integration tests (which mock `_emit_ask_telemetry`
itself and only inspect the kwargs passed to it), these tests leave the
real `_emit_ask_telemetry` -> `emit_ask_telemetry` -> `TelemetrySink.emit`
chain intact so that real `RuntimeEvent` objects (with auto-generated
`span_id`/`parent_event_id`) are produced and can be inspected.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sdd_runtime import RuntimeEvent


def _run_ask_capture_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    query: str = "hello",
) -> list[RuntimeEvent]:
    """Invoke ask_cmd with surrounding helpers mocked; return real RuntimeEvents."""
    from sdd_cli.commands._ask_backend import ask_cmd

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")

    (tmp_path / ".sdd" / "runtime").mkdir(parents=True)
    (tmp_path / ".sdd" / "profile").write_text(
        "[sdd]\nworkspace_id=test-ws\n", encoding="utf-8"
    )

    captured: list[RuntimeEvent] = []

    class _FakeSink:
        def __init__(self, **_):
            pass

        def emit(self, event: RuntimeEvent) -> None:
            captured.append(event)

    fake_profile = MagicMock()
    fake_profile.as_dict.return_value = {
        "profile": "client",
        "name": "test",
        "workspace_id": "test-ws",
        "core_hash": "abc",
        "root": tmp_path,
        "is_master": False,
        "is_client": True,
    }

    with (
        patch("sdd_cli.commands._ask_backend.TelemetrySink", _FakeSink),
        patch("sdd_core.utils.environment.resolve_profile", return_value=fake_profile),
        patch(
            "sdd_cli.commands._ask_backend._resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "sdd_cli.commands._ask_backend._get_profile_state",
            return_value=("client", "HEALTHY"),
        ),
        patch("sdd_cli.commands._ask_backend._guard_budget_breach"),
        patch("sdd_cli.commands._ask_backend._guard_handshake"),
        patch("sdd_cli.commands._ask_backend._write_runtime_cache"),
        patch("sdd_cli.commands._ask_backend._upsert_ask_session"),
        patch("sdd_cli.commands._ask_backend._emit_state_warnings"),
        patch(
            "sdd_cli.commands._ask_backend.build_governed_ask_snapshot",
            return_value={
                "query_hash": "bed9bd3e",
                "context_source": "compiled",
                "fingerprint": "abc",
                "mandates_count": 5,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "canonical",
                "drift_detected": False,
                "root_seed_drift_detected": False,
                "learning_signals": {},
                "learning_recommendation": None,
                "learning_context": {},
                "ask_decision_envelope": {},
            },
        ),
        patch(
            "sdd_cli.commands._ask_backend._run_organize_intake",
            return_value=(False, "light_input", None, 0, "indexed_only"),
        ),
        patch(
            "sdd_cli.commands._ask_backend._governance_footer_for_state",
            return_value="",
        ),
    ):
        ask_cmd(query=query)

    return captured


def test_phase_events_share_parent_trace_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _run_ask_capture_events(tmp_path, monkeypatch)

    parent = next(e for e in captured if e.event == "governance.ask")
    phases = [e for e in captured if e.event == "governance.ask.phase"]

    assert len(phases) > 0
    for phase in phases:
        assert phase.trace_id == parent.trace_id
        assert phase.parent_event_id == parent.span_id
        assert phase.span_id != parent.span_id


def test_phase_events_have_required_detail_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _run_ask_capture_events(tmp_path, monkeypatch)
    phases = [e for e in captured if e.event == "governance.ask.phase"]

    assert len(phases) > 0
    for phase in phases:
        assert "phase_id" in phase.details
        assert "latency_domain" in phase.details
        assert "measurement_quality" in phase.details
        assert "observed_by" in phase.details


def test_phase_events_cover_expected_phase_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _run_ask_capture_events(tmp_path, monkeypatch)
    phases = [e for e in captured if e.event == "governance.ask.phase"]

    phase_ids = {phase.details.get("phase_id") for phase in phases}
    assert phase_ids == {
        "ask.budget.guard",
        "ask.workspace.resolve",
        "ask.organize.intake",
        "ask.handshake.guard",
        "ask.profile.resolve",
        "ask.governance.snapshot",
    }


def test_parent_governance_ask_still_emits_current_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: parent event fields unaffected by phase instrumentation."""
    captured = _run_ask_capture_events(tmp_path, monkeypatch)
    parent = next(e for e in captured if e.event == "governance.ask")

    assert parent.duration_ms is not None
    assert parent.trace_id
    assert parent.command == "ask"
    assert parent.details.get("context_source") == "compiled"
    assert parent.details.get("mandates_loaded") == 5
    assert parent.details.get("ahp_state") == "HEALTHY"
    assert parent.details.get("profile") == "client"
