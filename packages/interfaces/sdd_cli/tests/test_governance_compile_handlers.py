"""Tests for sdd_cli.services.governance_compile_handlers."""

from __future__ import annotations

import configparser
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from rich.console import Console

from sdd_cli.services.governance_compile_handlers import (
    regenerate_seeds,
    resolve_output_base,
    run_compilation,
    run_compile,
    update_profile_hash,
)


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class TestResolveOutputBase:
    def test_no_override_returns_resolved_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_TEST_OUTPUT_DIR", raising=False)
        assert resolve_output_base(tmp_path) == tmp_path.resolve()

    def test_override_with_resolve_workspace_root_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", str(tmp_path / "redirected"))
        with patch(
            "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
            side_effect=RuntimeError("boom"),
        ):
            assert resolve_output_base(tmp_path) == tmp_path.resolve()

    def test_override_when_output_differs_from_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", str(tmp_path / "redirected"))
        other_ws = tmp_path / "other"
        with patch(
            "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
            return_value=other_ws,
        ):
            assert resolve_output_base(tmp_path) == tmp_path.resolve()

    def test_override_when_output_matches_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        redirected = tmp_path / "redirected"
        monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", str(redirected))
        with patch(
            "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            result = resolve_output_base(tmp_path)
        assert result == redirected.resolve()
        assert redirected.exists()


class _FakeOrchestrator:
    _RESULT: dict | None = {"full_pipeline_success": True, "phase_1": {}, "phase_2": {}}

    def __init__(self, profile: str | None = None) -> None:
        self.profile = profile

    def run_full_pipeline(self):
        return self._RESULT


class TestRunCompilation:
    def test_success_returns_result(self) -> None:
        with patch(
            "sdd_core.governance_orchestrator.GovernanceOrchestrator",
            _FakeOrchestrator,
        ):
            result = run_compilation(profile="client", console=_console())
        assert result["full_pipeline_success"] is True

    def test_default_console_created(self) -> None:
        with patch(
            "sdd_core.governance_orchestrator.GovernanceOrchestrator",
            _FakeOrchestrator,
        ):
            result = run_compilation(profile=None)
        assert result["full_pipeline_success"] is True

    def test_failure_raises_exit(self) -> None:
        class _Failing(_FakeOrchestrator):
            _RESULT = {"full_pipeline_success": False}

        with (
            patch("sdd_core.governance_orchestrator.GovernanceOrchestrator", _Failing),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_compilation(profile=None, console=_console())
        assert exc_info.value.exit_code == 1

    def test_empty_result_raises_exit(self) -> None:
        class _Empty(_FakeOrchestrator):
            _RESULT = {}

        with (
            patch("sdd_core.governance_orchestrator.GovernanceOrchestrator", _Empty),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_compilation(profile=None, console=_console())
        assert exc_info.value.exit_code == 1


def _write_profile(profile_path: Path) -> None:
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    parser = configparser.ConfigParser()
    parser["sdd"] = {"type": "client"}
    with open(profile_path, "w", encoding="utf-8") as f:
        parser.write(f)


class TestUpdateProfileHash:
    def test_empty_fingerprint_returns_early(self) -> None:
        update_profile_hash("", console=_console())

    def test_default_console_with_empty_fingerprint(self) -> None:
        update_profile_hash("")

    def test_updates_profile_with_given_fingerprint(self, tmp_path: Path) -> None:
        profile_path = tmp_path / ".sdd" / "profile"
        _write_profile(profile_path)
        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()

        console = _console()
        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.services.governance_compile_handlers.compiled_active_dir",
                return_value=compiled_dir,
            ),
        ):
            update_profile_hash("abcdef0123456789abcdef", console=console)

        parser = configparser.ConfigParser()
        parser.read(profile_path)
        assert parser["sdd"]["core_hash"] == "abcdef0123456789"[:16]
        assert "core_hash updated" in console.file.getvalue()

    def test_artifact_fingerprint_overrides_given_value(self, tmp_path: Path) -> None:
        profile_path = tmp_path / ".sdd" / "profile"
        _write_profile(profile_path)
        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        artifact_fp = "fedcba9876543210abcd"
        (compiled_dir / "governance-core.json").write_text(
            json.dumps({"fingerprint": artifact_fp}), encoding="utf-8"
        )

        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.services.governance_compile_handlers.compiled_active_dir",
                return_value=compiled_dir,
            ),
        ):
            update_profile_hash("0000000000000000", console=_console())

        parser = configparser.ConfigParser()
        parser.read(profile_path)
        assert parser["sdd"]["core_hash"] == artifact_fp[:16]

    def test_invalid_artifact_json_is_tolerated(self, tmp_path: Path) -> None:
        profile_path = tmp_path / ".sdd" / "profile"
        _write_profile(profile_path)
        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()
        (compiled_dir / "governance-core.json").write_text(
            "not valid json", encoding="utf-8"
        )

        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.services.governance_compile_handlers.compiled_active_dir",
                return_value=compiled_dir,
            ),
        ):
            update_profile_hash("0123456789abcdef0123", console=_console())

        parser = configparser.ConfigParser()
        parser.read(profile_path)
        assert parser["sdd"]["core_hash"] == "0123456789abcdef0123"[:16]

    def test_no_profile_file_does_nothing(self, tmp_path: Path) -> None:
        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()

        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.services.governance_compile_handlers.compiled_active_dir",
                return_value=compiled_dir,
            ),
        ):
            update_profile_hash("0123456789abcdef0123", console=_console())

    def test_profile_without_sdd_section_does_nothing(self, tmp_path: Path) -> None:
        profile_path = tmp_path / ".sdd" / "profile"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("[other]\nkey = value\n", encoding="utf-8")
        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir()

        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.services.governance_compile_handlers.compiled_active_dir",
                return_value=compiled_dir,
            ),
        ):
            update_profile_hash("0123456789abcdef0123", console=_console())

    def test_unexpected_exception_prints_warning(self) -> None:
        console = _console()
        with patch(
            "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
            side_effect=RuntimeError("boom"),
        ):
            update_profile_hash("0123456789abcdef0123", console=console)
        assert "WARN: could not update core_hash" in console.file.getvalue()


class TestRegenerateSeeds:
    def test_skip_env_var_returns_early(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SDD_SKIP_SEED_REGEN", "1")
        regenerate_seeds(console=_console())

    def test_default_console_with_skip_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SDD_SKIP_SEED_REGEN", "1")
        regenerate_seeds()

    def test_no_workspace_does_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SDD_SKIP_SEED_REGEN", raising=False)
        with patch(
            "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
            return_value=None,
        ):
            regenerate_seeds(console=_console())

    def test_success_with_wizard_available(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_SKIP_SEED_REGEN", raising=False)
        console = _console()
        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch("sdd_cli.utils.loader.validate_governance_path", return_value=True),
            patch(
                "sdd_cli.utils.loader.load_governance_config",
                return_value={"items": []},
            ),
            patch(
                "sdd_cli.generators.agent_seeds.generate_agent_instruction_files"
            ) as mock_gen_instr,
            patch(
                "sdd_wizard.contracts.generate_agent_instructions_from_config",
                return_value=True,
            ) as mock_gen_wizard,
        ):
            regenerate_seeds(console=console)

        mock_gen_instr.assert_called_once()
        mock_gen_wizard.assert_called_once()
        output = console.file.getvalue()
        assert "Agent instruction files regenerated" in output
        assert ".sdd/agent-instructions.md regenerated" in output

    def test_invalid_governance_path_uses_empty_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_SKIP_SEED_REGEN", raising=False)
        console = _console()
        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch("sdd_cli.utils.loader.validate_governance_path", return_value=False),
            patch(
                "sdd_cli.generators.agent_seeds.generate_agent_instruction_files"
            ) as mock_gen_instr,
            patch(
                "sdd_wizard.contracts.generate_agent_instructions_from_config",
                return_value=True,
            ),
        ):
            regenerate_seeds(console=console)

        args, _ = mock_gen_instr.call_args
        assert args[1] == {}

    def test_wizard_import_error_prints_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_SKIP_SEED_REGEN", raising=False)
        console = _console()
        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch("sdd_cli.utils.loader.validate_governance_path", return_value=True),
            patch(
                "sdd_cli.utils.loader.load_governance_config",
                return_value={"items": []},
            ),
            patch("sdd_cli.generators.agent_seeds.generate_agent_instruction_files"),
            patch.dict(sys.modules, {"sdd_wizard.contracts": None}),
        ):
            regenerate_seeds(console=console)

        assert "sdd_wizard not available" in console.file.getvalue()

    def test_generate_instruction_files_exception_prints_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_SKIP_SEED_REGEN", raising=False)
        console = _console()
        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch("sdd_cli.utils.loader.validate_governance_path", return_value=True),
            patch(
                "sdd_cli.utils.loader.load_governance_config",
                return_value={"items": []},
            ),
            patch(
                "sdd_cli.generators.agent_seeds.generate_agent_instruction_files",
                side_effect=RuntimeError("boom"),
            ),
        ):
            regenerate_seeds(console=console)

        assert "could not auto-regenerate agent files" in console.file.getvalue()


class TestRunCompile:
    def _success_patches(self):
        return (
            patch(
                "sdd_cli.services.governance_compile_handlers.run_compilation",
                return_value={
                    "phase_1": {"core_fingerprint": "a" * 64},
                    "phase_2": {},
                },
            ),
            patch("sdd_cli.services.governance_compile_handlers.update_profile_hash"),
            patch(
                "sdd_cli.services.governance_artifact_handlers.check_artifact_consistency",
                return_value=(True, ""),
            ),
            patch(
                "sdd_cli.services.governance_artifact_handlers.run_governance_compile_json",
                return_value=(
                    {
                        "status": "ok",
                        "ok": True,
                        "command": "governance compile",
                        "error": None,
                        "data": {},
                    },
                    False,
                ),
            ),
            patch(
                "sdd_cli.services.governance_command_output.render_governance_compile_table"
            ),
            patch(
                "sdd_cli.services.governance_compile_handlers.emit_compile_telemetry"
            ),
            patch("sdd_cli.services.governance_compile_handlers.regenerate_seeds"),
            patch(
                "sdd_cli.utils.sdd_authority.resolve_workspace_root",
                return_value=Path("/tmp/ws"),
            ),
        )

    def test_invalid_profile_raises_exit(self) -> None:
        with pytest.raises(typer.Exit) as exc_info:
            run_compile(profile="bogus", output_json=False, console=_console())
        assert exc_info.value.exit_code == 1

    def test_default_console_created(self) -> None:
        from contextlib import ExitStack

        with ExitStack() as stack:
            for p in self._success_patches():
                stack.enter_context(p)
            run_compile(profile=None, output_json=False, console=None)

    def test_valid_profile_success(self) -> None:
        from contextlib import ExitStack

        with ExitStack() as stack:
            for p in self._success_patches():
                stack.enter_context(p)
            run_compile(profile="client", output_json=False, console=_console())
