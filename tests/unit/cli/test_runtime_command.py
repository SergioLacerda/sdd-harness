"""Unit tests for `sdd runtime status` command.

Tests call the status() callback directly to bypass Typer's CliRunner,
patching AgentHandshakeProtocol.validate() and find_workspace_root.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from sdd_cli.commands.runtime import status

pytestmark = pytest.mark.unit


def _make_ahp_patch(state: str) -> MagicMock:
    report = MagicMock()
    instance = MagicMock()
    instance.validate.return_value = (state, report)
    instance.format_combined_output.return_value = f"[state={state}]"
    return instance


class TestRuntimeStatusCommand:
    """sdd runtime status exits with correct codes per AHP state."""

    def test_healthy_exits_0(self, tmp_path: Path) -> None:
        ahp_instance = _make_ahp_patch("HEALTHY")
        with (
            patch(
                "sdd_core.utils.environment.find_workspace_root", return_value=tmp_path
            ),
            patch(
                "sdd_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch("sdd_cli.commands.runtime._emit_runtime_status", return_value={}),
            patch("sdd_cli.commands.runtime._show_ask_confidence", return_value=""),
            patch("sdd_runtime.format_governance_footer", return_value=""),
        ):
            # HEALTHY → should not raise typer.Exit (exits 0 implicitly)
            status(ctx=MagicMock(), verbose=False, force=False)

    def test_partial_exits_0(self, tmp_path: Path) -> None:
        ahp_instance = _make_ahp_patch("PARTIAL")
        with (
            patch(
                "sdd_core.utils.environment.find_workspace_root", return_value=tmp_path
            ),
            patch(
                "sdd_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch("sdd_cli.commands.runtime._emit_runtime_status", return_value={}),
            patch("sdd_cli.commands.runtime._show_ask_confidence", return_value=""),
            patch("sdd_runtime.format_governance_footer", return_value=""),
        ):
            status(ctx=MagicMock(), verbose=False, force=False)

    def test_not_initialized_exits_1(self, tmp_path: Path) -> None:
        ahp_instance = _make_ahp_patch("NOT_INITIALIZED")
        with (
            pytest.raises(typer.Exit) as exc_info,
            patch(
                "sdd_core.utils.environment.find_workspace_root", return_value=tmp_path
            ),
            patch(
                "sdd_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch("sdd_cli.commands.runtime._emit_runtime_status", return_value={}),
            patch("sdd_cli.commands.runtime._show_ask_confidence", return_value=""),
            patch("sdd_runtime.format_governance_footer", return_value=""),
        ):
            status(ctx=MagicMock(), verbose=False, force=False)
        assert exc_info.value.exit_code == 1

    def test_misconfigured_exits_2(self, tmp_path: Path) -> None:
        ahp_instance = _make_ahp_patch("MISCONFIGURED")
        with (
            pytest.raises(typer.Exit) as exc_info,
            patch(
                "sdd_core.utils.environment.find_workspace_root", return_value=tmp_path
            ),
            patch(
                "sdd_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch("sdd_cli.commands.runtime._emit_runtime_status", return_value={}),
            patch("sdd_cli.commands.runtime._show_ask_confidence", return_value=""),
            patch("sdd_runtime.format_governance_footer", return_value=""),
        ):
            status(ctx=MagicMock(), verbose=False, force=False)
        assert exc_info.value.exit_code == 2

    def test_no_workspace_exits_3(self) -> None:
        ahp_instance = _make_ahp_patch("NOT_CONNECTED")
        with (
            pytest.raises(typer.Exit) as exc_info,
            patch(
                "sdd_cli.commands.runtime.resolve_workspace_root",
                return_value=Path("/tmp/nonexistent"),
            ),
            patch(
                "sdd_core.governance.handshake.AgentHandshakeProtocol",
                return_value=ahp_instance,
            ),
            patch("sdd_cli.commands.runtime._emit_runtime_status", return_value={}),
            patch("sdd_cli.commands.runtime._show_ask_confidence", return_value=""),
            patch("sdd_runtime.format_governance_footer", return_value=""),
        ):
            status(ctx=MagicMock(), verbose=False, force=False)
        assert exc_info.value.exit_code == 3


class TestShowAskConfidence:
    """Tests for the internal _show_ask_confidence helper."""

    def test_no_state_file_returns_silently(self, tmp_path: Path) -> None:
        from sdd_cli.commands.runtime import _show_ask_confidence

        # No .sdd/runtime/governance-state.json → should not raise
        _show_ask_confidence(tmp_path)

    def test_state_file_without_last_ask_returns_silently(self, tmp_path: Path) -> None:
        import json

        from sdd_cli.commands.runtime import _show_ask_confidence

        runtime_dir = tmp_path / ".sdd" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "governance-state.json").write_text(
            json.dumps({"state": "HEALTHY"}), encoding="utf-8"
        )
        _show_ask_confidence(tmp_path)

    def test_state_file_with_last_ask_echoes_fields(self, tmp_path: Path) -> None:
        import json

        from sdd_cli.commands.runtime import _show_ask_confidence

        runtime_dir = tmp_path / ".sdd" / "runtime"
        runtime_dir.mkdir(parents=True)
        last_ask = {
            "ts": "2025-01-01T00:00:00",
            "context_source": "compiled",
            "compiled_fingerprint_used": "abc123def",
            "mandates_loaded": 3,
            "agent_id": "test-agent",
        }
        (runtime_dir / "governance-state.json").write_text(
            json.dumps({"state": "HEALTHY", "last_ask": last_ask}), encoding="utf-8"
        )

        echoed: list[str] = []
        with patch("typer.echo", side_effect=lambda s, **kw: echoed.append(str(s))):
            _show_ask_confidence(tmp_path)

        combined = "\n".join(echoed)
        assert "ask_confidence" in combined
        assert "compiled" in combined

    def test_state_file_with_trace_id_shows_truncated(self, tmp_path: Path) -> None:
        import json

        from sdd_cli.commands.runtime import _show_ask_confidence

        runtime_dir = tmp_path / ".sdd" / "runtime"
        runtime_dir.mkdir(parents=True)
        last_ask = {
            "ts": "2025-01-01T00:00:00",
            "context_source": "none",
            "compiled_fingerprint_used": "",
            "mandates_loaded": 0,
            "agent_id": "agent-1",
            "trace_id": "abc123def456789",
        }
        (runtime_dir / "governance-state.json").write_text(
            json.dumps({"state": "HEALTHY", "last_ask": last_ask}), encoding="utf-8"
        )

        echoed: list[str] = []
        with patch("typer.echo", side_effect=lambda s, **kw: echoed.append(str(s))):
            _show_ask_confidence(tmp_path)

        combined = "\n".join(echoed)
        assert "trace_id" in combined
        assert "abc123de" in combined  # first 8 chars

    def test_malformed_json_does_not_raise(self, tmp_path: Path) -> None:
        from sdd_cli.commands.runtime import _show_ask_confidence

        runtime_dir = tmp_path / ".sdd" / "runtime"
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "governance-state.json").write_text(
            "not-valid-json", encoding="utf-8"
        )

        # Should not raise
        _show_ask_confidence(tmp_path)
