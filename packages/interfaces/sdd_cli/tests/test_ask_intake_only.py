"""Tests for `sdd ask --intake-only` — the cheap hook-mode profile.

Spike follow-up: 20260714-sdd-ask-single-entrypoint-spike (A-005/I-005/I-006).
`--intake-only` must compute execution_gate/intake_index_mode/intent without
loading the full compiled-governance snapshot or emitting telemetry, and must
never claim the full `sdd ask` behavior changed for callers that omit the flag.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd_cli.main import app

runner = CliRunner()


def _parse_result_json(output: str) -> dict:
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            raise
        return json.loads(lines[-1])


def _patch_cheap_session(tmp_path: Path, *, organize_used: bool, organize_reason: str):
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
    return (
        patch(
            "sdd_cli.commands._ask_backend._resolve_workspace_root",
            return_value=tmp_path,
        ),
        patch(
            "sdd_core.utils.environment.resolve_profile",
            return_value=fake_profile,
        ),
        patch(
            "sdd_cli.commands._ask_backend._get_profile_state",
            return_value=("client", "HEALTHY"),
        ),
        patch("sdd_cli.commands._ask_backend._guard_budget_breach"),
        patch("sdd_cli.commands._ask_backend._guard_handshake"),
        patch(
            "sdd_cli.commands._ask_backend._run_organize_intake",
            return_value=(organize_used, organize_reason, "", 0, "indexed_only"),
        ),
    )


def test_intake_only_text_response_skips_governance_snapshot_and_telemetry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from sdd_cli.commands._ask_backend import ask_cmd

    monkeypatch.setenv("SDD_AGENT_ID", "test-agent")
    patches = _patch_cheap_session(
        tmp_path, organize_used=False, organize_reason="light_input"
    )
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patch(
            "sdd_cli.commands._ask_backend.build_governed_ask_snapshot"
        ) as mock_snapshot,
        patch("sdd_cli.commands._ask_backend._emit_ask_telemetry") as mock_telemetry,
        patch("sdd_cli.commands._ask_backend._write_runtime_cache") as mock_cache,
        patch("sdd_cli.commands._ask_backend._upsert_ask_session") as mock_upsert,
    ):
        ask_cmd(query="short query", intake_only=True)

    mock_snapshot.assert_not_called()
    mock_telemetry.assert_not_called()
    mock_cache.assert_not_called()
    mock_upsert.assert_not_called()

    stdout = capsys.readouterr().out
    assert "execution_gate    : allowed" in stdout
    assert "intake_index_mode : none" in stdout
    assert "intake_profile    : cheap" in stdout
    assert "intent            : governance_query" in stdout
    assert "delegation_executed : false" in stdout
    assert "provider_bound    : false" in stdout


def test_intake_only_json_response_matches_full_gate_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SDD_ASK_ENTRYPOINT", raising=False)
    patches = _patch_cheap_session(
        tmp_path, organize_used=False, organize_reason="index_unavailable"
    )
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patch(
            "sdd_core.governance.handshake.AgentHandshakeProtocol.validate",
            return_value=("HEALTHY", None),
        ),
        patch(
            "sdd_cli.commands._ask_backend.build_governed_ask_snapshot"
        ) as mock_snapshot,
        patch("sdd_cli.commands._ask_backend._emit_ask_telemetry") as mock_telemetry,
        patch("sdd_cli.commands._ask_backend._write_runtime_cache"),
        patch("sdd_cli.commands._ask_backend._upsert_ask_session"),
    ):
        result = runner.invoke(
            app, ["--json", "ask", "--intake-only", "implementar mudanca"]
        )

    assert result.exit_code == 0, result.output
    mock_snapshot.assert_not_called()
    mock_telemetry.assert_not_called()

    payload = _parse_result_json(result.output)
    data = payload["data"]
    assert data["execution_gate"] == "blocked"
    assert data["intake_index_mode"] == "none"
    assert data["intake_profile"] == "cheap"
    assert data["intent"] == "implementation_request"
    assert data["delegation_executed"] is False
    assert data["provider_bound"] is False
    # The cheap profile must not fabricate governance fields it never loaded.
    assert "fingerprint" not in data
    assert "runtime_handbook" not in data


def test_default_ask_without_intake_only_flag_still_loads_full_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full explicit `sdd ask` behavior (no --intake-only) is unchanged."""
    patches = _patch_cheap_session(
        tmp_path, organize_used=False, organize_reason="light_input"
    )
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patch(
            "sdd_core.governance.handshake.AgentHandshakeProtocol.validate",
            return_value=("HEALTHY", None),
        ),
        patch(
            "sdd_cli.commands._ask_backend.build_governed_ask_snapshot",
            return_value={
                "context_source": "compiled",
                "fingerprint": "fp-1",
                "mandates_count": 1,
                "authenticated": True,
                "degraded": False,
                "degrade_reason": "",
                "trust_source": "verified",
                "drift_detected": False,
                "root_seed_drift_detected": False,
                "learning_signals": {
                    "diagnosis_inconclusive": 0,
                    "evidence_insufficient": 0,
                    "scope_violation": 0,
                    "drift_recent_failures": 0,
                    "observed_events": 0,
                    "window_days": 7,
                },
            },
        ) as mock_snapshot,
        patch("sdd_cli.commands._ask_backend._emit_ask_telemetry") as mock_telemetry,
        patch("sdd_cli.commands._ask_backend._write_runtime_cache"),
        patch("sdd_cli.commands._ask_backend._upsert_ask_session"),
    ):
        result = runner.invoke(app, ["--json", "ask", "status?"])

    assert result.exit_code == 0, result.output
    mock_snapshot.assert_called_once()
    assert mock_telemetry.call_count >= 1
