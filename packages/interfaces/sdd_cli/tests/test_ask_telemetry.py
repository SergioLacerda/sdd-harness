"""Tests for sdd ask telemetry fixes — duration, tokens, path_id, OtelBridge."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd_cli.commands._ask_backend import _resolve_tokens
from sdd_cli.main import app


def _make_fake_ahp(state: str):
    class _FakeAHP:
        def __init__(self, project_root=None):
            self.skill_profile = "default"

        def validate(self, output_mode="silent", force_recheck=False):
            class _R:
                confidence = 90.0

            return state, _R()

        def is_handshake_valid(self, strict=False):
            return True

    return _FakeAHP


# ---------------------------------------------------------------------------
# _resolve_tokens
# ---------------------------------------------------------------------------


def test_tokens_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDD_TOKENS_INPUT", "100")
    monkeypatch.setenv("SDD_TOKENS_OUTPUT", "200")
    t_in, t_out, source = _resolve_tokens("hello", "world output")
    assert t_in == 100
    assert t_out == 200
    assert source == "env"


def test_tokens_estimated_from_lengths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_TOKENS_INPUT", raising=False)
    monkeypatch.delenv("SDD_TOKENS_OUTPUT", raising=False)
    query = "a" * 40
    output = "b" * 80
    t_in, t_out, source = _resolve_tokens(query, output)
    assert t_in == 40 // 4
    assert t_out == 80 // 4
    assert source == "estimated"


def test_tokens_none_when_empty_and_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_TOKENS_INPUT", raising=False)
    monkeypatch.delenv("SDD_TOKENS_OUTPUT", raising=False)
    t_in, t_out, source = _resolve_tokens("", "")
    assert t_in is None
    assert t_out is None
    assert source == "estimated"


def test_tokens_env_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDD_TOKENS_INPUT", "50")
    monkeypatch.delenv("SDD_TOKENS_OUTPUT", raising=False)
    output = "x" * 100
    t_in, t_out, source = _resolve_tokens("query", output)
    assert t_in == 50
    assert t_out == 100 // 4
    assert source == "env"


# ---------------------------------------------------------------------------
# _emit_ask_telemetry — duration, start_ts, end_ts, path_id
# ---------------------------------------------------------------------------


def _make_emit_kwargs(**overrides):
    base = dict(
        command="ask",
        workspace_root=Path("/tmp/fake-ws"),
        trace_id="trace-abc",
        agent_id="test-agent",
        fingerprint="abc123",
        context_source="compiled",
        mandates_count=5,
        profile="client",
        state="HEALTHY",
        drift_detected=False,
    )
    base.update(overrides)
    return base


def _event_path_id(event: object) -> str | None:
    """Read path_id from either event object or dict payload."""
    if isinstance(event, dict):
        return event.get("path_id")
    return getattr(event, "path_id", None)


def test_duration_and_timestamps_passed_to_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sdd_cli.commands._ask_backend import _emit_ask_telemetry

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    (tmp_path / ".sdd" / "runtime").mkdir(parents=True)
    (tmp_path / ".sdd" / "profile").write_text(
        "[sdd]\nworkspace_id=test-ws\n", encoding="utf-8"
    )

    captured: list = []

    class _FakeSink:
        def __init__(self, **_):
            pass

        def emit(self, event):
            captured.append(event)

    with patch("sdd_cli.commands._ask_backend.TelemetrySink", _FakeSink):
        _emit_ask_telemetry(
            "governance.ask",
            **_make_emit_kwargs(workspace_root=tmp_path),
            start_ts="2026-05-20T00:00:00Z",
            end_ts="2026-05-20T00:00:01Z",
            duration_ms=42,
            path_id="PATH_A",
        )

    assert len(captured) == 1
    ev = captured[0]
    assert ev.duration_ms == 42
    assert ev.start_ts == "2026-05-20T00:00:00Z"
    assert ev.end_ts == "2026-05-20T00:00:01Z"
    assert _event_path_id(ev) == "PATH_A"


# ---------------------------------------------------------------------------
# path_id inference (light vs heavy intake)
# Approach: mock _emit_ask_telemetry directly to capture the path_id kwarg.
# This avoids the CliRunner → TelemetrySink chain that is fragile across
# Python versions and containerised environments.
# ---------------------------------------------------------------------------


def _run_ask_capture_path_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    query: str,
) -> str | None:
    """Invoke ask_cmd with key dependencies mocked; return path_id passed to telemetry."""
    from sdd_cli.commands._ask_backend import ask_cmd

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")

    captured_kwargs: list[dict] = []

    def _fake_emit(_event_name: str, **kwargs: object) -> None:
        captured_kwargs.append(kwargs)

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
        patch(
            "sdd_cli.commands._ask_backend._emit_ask_telemetry", side_effect=_fake_emit
        ),
        patch(
            "sdd_core.utils.environment.resolve_profile",
            return_value=fake_profile,
        ),
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
            "sdd_cli.services.ask_snapshot.build_governed_ask_snapshot",
            return_value={
                "context_source": "compiled",
                "fingerprint": "abc",
                "mandates_count": 5,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "canonical",
                "drift_detected": False,
                "learning_recommendation": None,
                "learning_context": {},
                "ask_decision_envelope": {},
            },
        ),
        patch(
            "sdd_cli.commands._ask_backend._run_organize_intake",
            return_value=(
                len(query) >= 6000,
                "char_count>=6000" if len(query) >= 6000 else "light_input",
                None,
                0,
                "indexed_only",
            ),
        ),
        patch(
            "sdd_cli.commands._ask_backend._governance_footer_for_state",
            return_value="",
        ),
    ):
        ask_cmd(query=query)

    if not captured_kwargs:
        return None
    return str(captured_kwargs[0].get("path_id", ""))


def test_path_id_light_intake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_PATH_ID", raising=False)
    path_id = _run_ask_capture_path_id(tmp_path, monkeypatch, "short query")
    assert path_id == "PATH_A"


def test_path_id_heavy_intake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDD_PATH_ID", raising=False)
    path_id = _run_ask_capture_path_id(tmp_path, monkeypatch, "x" * 6001)
    assert path_id == "PATH_B"


def test_path_id_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SDD_PATH_ID", "PATH_CUSTOM")
    path_id = _run_ask_capture_path_id(tmp_path, monkeypatch, "short query")
    assert path_id == "PATH_CUSTOM"


def test_ask_runtime_cache_uses_effective_degraded_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sdd_cli.commands._ask_backend import ask_cmd

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")

    captured_emit: list[dict] = []
    captured_cache: list[dict] = []

    def _fake_emit(_event_name: str, **kwargs: object) -> None:
        captured_emit.append(kwargs)

    def _fake_cache(_workspace_root: Path, last_ask: dict[str, object]) -> None:
        captured_cache.append(last_ask)

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
        patch(
            "sdd_cli.commands._ask_backend._emit_ask_telemetry", side_effect=_fake_emit
        ),
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
        patch("sdd_cli.commands._ask_backend._write_runtime_cache", _fake_cache),
        patch("sdd_cli.commands._ask_backend._upsert_ask_session"),
        patch("sdd_cli.commands._ask_backend._emit_state_warnings"),
        patch(
            "sdd_cli.commands._ask_backend.build_governed_ask_snapshot",
            return_value={
                "query_hash": "bed9bd3e",
                "context_source": "compiled",
                "fingerprint": "abc",
                "mandates_count": 5,
                "authenticated": False,
                "degraded": True,
                "degrade_reason": "",
                "trust_source": "none",
                "drift_detected": False,
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
        ask_cmd(query="short query")

    assert captured_emit
    assert captured_cache
    emit_reason = captured_emit[0]["extra_details"]["degraded_reason"]
    cache_reason = captured_cache[0]["degraded_reason"]
    assert emit_reason == "artifact_unverified"
    assert cache_reason == emit_reason


def test_ask_telemetry_emits_token_source_estimated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sdd_cli.commands._ask_backend import ask_cmd

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")
    monkeypatch.delenv("SDD_TOKENS_INPUT", raising=False)
    monkeypatch.delenv("SDD_TOKENS_OUTPUT", raising=False)

    captured_kwargs: list[dict] = []

    def _fake_emit(_event_name: str, **kwargs: object) -> None:
        captured_kwargs.append(kwargs)

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
        patch(
            "sdd_cli.commands._ask_backend._emit_ask_telemetry", side_effect=_fake_emit
        ),
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
            "sdd_cli.services.ask_snapshot.build_governed_ask_snapshot",
            return_value={
                "context_source": "compiled",
                "fingerprint": "abc",
                "mandates_count": 5,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "canonical",
                "drift_detected": False,
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
        ask_cmd(query="short query")

    assert captured_kwargs
    extra_details = captured_kwargs[0].get("extra_details", {})
    assert isinstance(extra_details, dict)
    assert extra_details.get("token_source") == "estimated"


def test_ask_json_context_prefers_summary_full_when_env_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SDD_ASK_PREFER_FULL_SUMMARY", "true")
    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")
    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    runner = CliRunner()

    captured_requests: list[object] = []

    class _FakeContextLoader:
        def load_result(self, request):  # noqa: ANN001
            from types import SimpleNamespace

            captured_requests.append(request)
            return SimpleNamespace(
                items=["M001: Rule"],
                source="artifact",
                matched=1,
                truncated=False,
                bytes_loaded=12,
                compression_ratio=None,
            )

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
        patch("sdd_cli.commands._ask_backend._emit_ask_telemetry"),
        patch(
            "sdd_cli.services.ask_snapshot.build_governed_ask_snapshot",
            return_value={
                "context_source": "compiled",
                "fingerprint": "abc",
                "mandates_count": 1,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "canonical",
                "drift_detected": False,
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
        patch("sdd_runtime.context.ContextLoader", _FakeContextLoader),
        patch(
            "sdd_core.governance.handshake.AgentHandshakeProtocol",
            _make_fake_ahp("HEALTHY"),
        ),
    ):
        result = runner.invoke(app, ["--json", "ask", "--dossier", "status?"])

    assert result.exit_code == 0, result.output

    assert captured_requests, "ContextRequest should be created in --json flow"
    assert bool(getattr(captured_requests[0], "prefer_full_summary", False)) is True


def test_normalize_typer_value_optioninfo() -> None:
    from typer import Option

    from sdd_cli.commands._ask_backend import _normalize_typer_value

    value = Option(None, "--skill")
    assert _normalize_typer_value(value, "fallback") == "fallback"
    assert _normalize_typer_value("ok", "fallback") == "ok"


# ---------------------------------------------------------------------------
# OtelBridge opt-in
# ---------------------------------------------------------------------------


def test_otel_bridge_used_when_endpoint_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sdd_cli.commands._ask_backend import _emit_ask_telemetry

    monkeypatch.setenv("SDD_OTEL_ENDPOINT", "http://otel.example.com:4318")
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "profile").write_text(
        "[sdd]\nworkspace_id=test-ws\n", encoding="utf-8"
    )

    mock_bridge_instance = MagicMock()
    mock_bridge_cls = MagicMock(return_value=mock_bridge_instance)
    mock_exporter = MagicMock()
    mock_exporter_cls = MagicMock(return_value=mock_exporter)

    with (
        patch("sdd_cli.commands._ask_backend.OtelBridge", mock_bridge_cls, create=True),
        patch(
            "sdd_cli.commands._ask_backend.OtlpHttpExporter",
            mock_exporter_cls,
            create=True,
        ),
        patch("sdd_runtime.OtelBridge", mock_bridge_cls),
        patch("sdd_runtime.otel.OtlpHttpExporter", mock_exporter_cls),
    ):
        _emit_ask_telemetry(
            "governance.ask",
            **_make_emit_kwargs(workspace_root=tmp_path),
        )

    mock_bridge_instance.emit.assert_called_once()


def test_telemetry_sink_used_without_otel_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sdd_cli.commands._ask_backend import _emit_ask_telemetry

    monkeypatch.delenv("SDD_OTEL_ENDPOINT", raising=False)
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "profile").write_text(
        "[sdd]\nworkspace_id=test-ws\n", encoding="utf-8"
    )

    captured: list = []

    class _FakeSink:
        def __init__(self, **_):
            pass

        def emit(self, event):
            captured.append(event)

    with patch("sdd_cli.commands._ask_backend.TelemetrySink", _FakeSink):
        _emit_ask_telemetry(
            "governance.ask",
            **_make_emit_kwargs(workspace_root=tmp_path),
        )

    assert len(captured) == 1


def test_capture_effective_tokens_prefers_direct_values() -> None:
    from sdd_cli.commands._ask_backend import _capture_effective_tokens

    t_in, t_out = _capture_effective_tokens(12, 34)
    assert (t_in, t_out) == (12, 34)


def test_capture_effective_tokens_env_source(monkeypatch: pytest.MonkeyPatch) -> None:
    from sdd_cli.commands._ask_backend import _capture_effective_tokens

    monkeypatch.setenv("SDD_TOKENS_INPUT", "56")
    monkeypatch.setenv("SDD_TOKENS_OUTPUT", "78")
    t_in, t_out = _capture_effective_tokens(None, None)
    assert (t_in, t_out) == (56, 78)
