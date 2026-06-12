"""Tests for sdd_cli.services.governance_generate_handlers."""

from __future__ import annotations

import io
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from rich.console import Console

from sdd_cli.services.governance_generate_handlers import (
    complete_bootstrap_handshake,
    generate_adapters_safe,
    generate_artifacts,
    generate_seeds,
    resolve_generate_path,
    run_bootstrap_signing,
    run_generate,
    run_generate_phases,
    write_instruction_files_safe,
    write_prompt_commands_safe,
)


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


class TestResolveGeneratePath:
    def test_returns_path_when_given(self) -> None:
        assert resolve_generate_path("/some/path") == "/some/path"

    def test_no_workspace_raises_exit(self) -> None:
        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=None,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            resolve_generate_path("")
        assert exc_info.value.exit_code == 1

    def test_empty_path_resolves_to_compiled_dir(self, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.enforce_path_policy",
                side_effect=lambda root, **_: root,
            ),
        ):
            result = resolve_generate_path("")
        assert result == str(tmp_path / ".sdd" / "compiled")


class TestGenerateSeeds:
    def test_returns_seeds_info_and_dir(self, tmp_path: Path) -> None:
        fake_seeds_info = [("copilot", tmp_path / "a.md", "ok")]
        with patch(
            "sdd_cli.services.governance_generate_handlers.generate_agent_seeds",
            return_value=fake_seeds_info,
        ) as mock_gen:
            seeds_info, seeds_dir = generate_seeds(str(tmp_path), {"items": []})
        assert seeds_info == fake_seeds_info
        assert seeds_dir == tmp_path / ".vscode" / "agents"
        mock_gen.assert_called_once_with(seeds_dir, {"items": []})


class TestWriteInstructionFilesSafe:
    def test_success_prints_written_message(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "sdd_cli.services.governance_generate_handlers.generate_agent_instruction_files",
            return_value=[("copilot", tmp_path / "a.md")],
        ):
            write_instruction_files_safe(tmp_path, {}, console=console)
        output = console.file.getvalue()
        assert "copilot instructions written to" in output

    def test_exception_prints_warning(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "sdd_cli.services.governance_generate_handlers.generate_agent_instruction_files",
            side_effect=RuntimeError("boom"),
        ):
            write_instruction_files_safe(tmp_path, {}, console=console)
        output = console.file.getvalue()
        assert "could not write instruction files" in output


class TestWritePromptCommandsSafe:
    def test_success_prints_written_message(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "sdd_cli.services.governance_generate_handlers.generate_agent_prompt_commands",
            return_value=[("codex", tmp_path / "commands.md")],
        ):
            write_prompt_commands_safe(tmp_path, {}, console=console)
        output = console.file.getvalue()
        assert "codex prompt commands written to" in output

    def test_exception_prints_warning(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "sdd_cli.services.governance_generate_handlers.generate_agent_prompt_commands",
            side_effect=RuntimeError("boom"),
        ):
            write_prompt_commands_safe(tmp_path, {}, console=console)
        output = console.file.getvalue()
        assert "could not write prompt command files" in output


class TestGenerateAdaptersSafe:
    def test_success_with_files_written(self, tmp_path: Path) -> None:
        console = _console()
        result = MagicMock(success=True, files_written=["a", "b"], errors=[])
        fake_gen = MagicMock()
        fake_gen.generate.return_value = {"claude": result}
        with patch(
            "sdd_adapters.adapter_generator.AdapterGenerator", return_value=fake_gen
        ):
            generate_adapters_safe(tmp_path, console=console)
        output = console.file.getvalue()
        assert "Adapters (claude): 2 files written" in output

    def test_errors_print_warnings(self, tmp_path: Path) -> None:
        console = _console()
        result = MagicMock(success=False, files_written=[], errors=["bad thing"])
        fake_gen = MagicMock()
        fake_gen.generate.return_value = {"claude": result}
        with patch(
            "sdd_adapters.adapter_generator.AdapterGenerator", return_value=fake_gen
        ):
            generate_adapters_safe(tmp_path, console=console)
        output = console.file.getvalue()
        assert "WARN: adapter claude: bad thing" in output

    def test_exception_prints_warning(self, tmp_path: Path) -> None:
        console = _console()
        with patch(
            "sdd_adapters.adapter_generator.AdapterGenerator",
            side_effect=RuntimeError("boom"),
        ):
            generate_adapters_safe(tmp_path, console=console)
        output = console.file.getvalue()
        assert "could not generate adapter files" in output


class TestRunGeneratePhases:
    def test_all_phases_succeed(self, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_cli.generators._skills.generate_skills_registry",
                return_value={"skill_count": 5},
            ),
            patch(
                "sdd_cli.generators._commands.generate_commands_registry",
                return_value={"command_count": 3},
            ),
            patch(
                "sdd_cli.generators._indices.generate_skill_index",
                return_value={"skill_count": 5},
            ),
            patch(
                "sdd_cli.generators._indices.generate_cli_commands_index",
                return_value={"command_count": 3},
            ),
        ):
            result = run_generate_phases(str(tmp_path), {})
        assert result == (True, True, True)

    def test_zero_counts_yield_false_flags(self, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_cli.generators._skills.generate_skills_registry",
                return_value={"skill_count": 0},
            ),
            patch(
                "sdd_cli.generators._commands.generate_commands_registry",
                return_value={"command_count": 0},
            ),
            patch(
                "sdd_cli.generators._indices.generate_skill_index",
                return_value={"skill_count": 0},
            ),
            patch(
                "sdd_cli.generators._indices.generate_cli_commands_index",
                return_value={"command_count": 0},
            ),
        ):
            result = run_generate_phases(str(tmp_path), {})
        assert result == (False, False, False)

    def test_all_phases_raise_are_tolerated(self, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_cli.generators._skills.generate_skills_registry",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "sdd_cli.generators._commands.generate_commands_registry",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "sdd_cli.generators._indices.generate_skill_index",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "sdd_cli.generators._indices.generate_cli_commands_index",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = run_generate_phases(str(tmp_path), {})
        assert result == (False, False, False)


class _FakeChallenge:
    def __init__(self) -> None:
        self.active_mandates = ["M001", "M002"]
        self.available_skills = [
            {"name": "sdd-ask"},
            {"name": "sdd-organize"},
            "not-a-dict",
            {"no_name": "x"},
            {"name": 123},
        ]


class _FakeAHP:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def generate_challenge(
        self, task_description: str = "General Task"
    ) -> _FakeChallenge:
        assert task_description == "Bootstrap Session"
        return _FakeChallenge()

    def complete_handshake(self, response: dict) -> None:
        self.response = response


class TestCompleteBootstrapHandshake:
    def test_filters_invalid_skill_entries(self) -> None:
        captured: dict = {}

        class _CapturingAHP(_FakeAHP):
            def complete_handshake(self, response: dict) -> None:
                captured.update(response)

        with patch(
            "sdd_core.governance.handshake.AgentHandshakeProtocol", _CapturingAHP
        ):
            complete_bootstrap_handshake()

        assert captured["skills_to_use"] == ["sdd-ask", "sdd-organize"]
        assert captured["understood_mandates"] == ["M001", "M002"]
        assert captured["acknowledged_signature"] is True
        assert captured["compliance_declaration"] is True


class TestRunBootstrapSigning:
    def test_normal_flow_signs_once(self, tmp_path: Path) -> None:
        keygen_fn = MagicMock()
        sign_fn = MagicMock()
        with patch(
            "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)

        keygen_fn.assert_called_once_with(key_id="dev-01", output_dir=".sdd/trust")
        sign_fn.assert_called_once_with(
            key_id="dev-01", key_path=None, compiled_dir=None, source=False
        )

    def test_keygen_exit_zero_is_tolerated(self, tmp_path: Path) -> None:
        keygen_fn = MagicMock(side_effect=typer.Exit(0))
        sign_fn = MagicMock()
        with patch(
            "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)
        sign_fn.assert_called_once()

    def test_keygen_exit_nonzero_is_reraised(self, tmp_path: Path) -> None:
        keygen_fn = MagicMock(side_effect=typer.Exit(1))
        sign_fn = MagicMock()
        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)
        assert exc_info.value.exit_code == 1
        sign_fn.assert_not_called()

    def test_source_artifact_present_signs_twice(self, tmp_path: Path) -> None:
        source_dir = tmp_path / ".sdd" / "source"
        source_dir.mkdir(parents=True)
        (source_dir / "governance-core.json").write_text("{}", encoding="utf-8")

        keygen_fn = MagicMock()
        sign_fn = MagicMock()
        with patch(
            "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)

        assert sign_fn.call_count == 2
        sign_fn.assert_any_call(
            key_id="dev-01", key_path=None, compiled_dir=None, source=True
        )

    def test_no_workspace_skips_source_sign(self) -> None:
        keygen_fn = MagicMock()
        sign_fn = MagicMock()
        with patch(
            "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
            return_value=None,
        ):
            run_bootstrap_signing("dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn)
        sign_fn.assert_called_once()


class TestGenerateArtifacts:
    def _common_patches(self, tmp_path: Path, *, items: list | None = None):
        items = items if items is not None else [{"id": "M001"}]
        return (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_generate_path",
                return_value=str(tmp_path / "compiled"),
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.validate_governance_path",
                return_value=True,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.load_governance_config",
                return_value={"items": items},
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_output_base",
                side_effect=lambda p: p,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.generate_seeds",
                return_value=(
                    [("copilot", tmp_path / "a.md", "ok")],
                    tmp_path / "seeds",
                ),
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.run_generate_phases",
                return_value=(True, True, True),
            ),
        )

    def test_invalid_governance_path_exits(self, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_generate_path",
                return_value=str(tmp_path / "compiled"),
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.validate_governance_path",
                return_value=False,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            generate_artifacts(
                output_dir=str(tmp_path), path="", output_json=False, console=_console()
            )
        assert exc_info.value.exit_code == 1

    def test_missing_items_exits(self, tmp_path: Path) -> None:
        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_generate_path",
                return_value=str(tmp_path / "compiled"),
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.validate_governance_path",
                return_value=True,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.load_governance_config",
                return_value={"items": []},
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            generate_artifacts(
                output_dir=str(tmp_path), path="", output_json=False, console=_console()
            )
        assert exc_info.value.exit_code == 1

    def test_output_dir_none_resolves_workspace_root(self, tmp_path: Path) -> None:
        with ExitStack() as stack:
            for p in self._common_patches(tmp_path):
                stack.enter_context(p)
            stack.enter_context(
                patch(
                    "sdd_cli.services.governance_generate_handlers.render_generate_table"
                )
            )
            stack.enter_context(
                patch(
                    "sdd_cli.services.governance_generate_handlers.write_instruction_files_safe"
                )
            )
            stack.enter_context(
                patch(
                    "sdd_cli.services.governance_generate_handlers.write_prompt_commands_safe"
                )
            )
            stack.enter_context(
                patch(
                    "sdd_cli.services.governance_generate_handlers.generate_adapters_safe"
                )
            )
            generate_artifacts(
                output_dir=None, path="", output_json=False, console=_console()
            )

    def test_output_json_emits_payload(self, tmp_path: Path) -> None:
        with ExitStack() as stack:
            for p in self._common_patches(tmp_path):
                stack.enter_context(p)
            mock_json = stack.enter_context(
                patch(
                    "sdd_cli.services.governance_generate_handlers.run_governance_generate_json",
                    return_value={"status": "ok"},
                )
            )
            mock_emit = stack.enter_context(
                patch("sdd_cli.services.governance_generate_handlers.emit_json")
            )
            generate_artifacts(
                output_dir=str(tmp_path), path="", output_json=True, console=_console()
            )
        mock_json.assert_called_once()
        mock_emit.assert_called_once_with({"status": "ok"})

    def test_non_json_renders_table_and_writes_files(self, tmp_path: Path) -> None:
        with ExitStack() as stack:
            for p in self._common_patches(tmp_path):
                stack.enter_context(p)
            mock_table = stack.enter_context(
                patch(
                    "sdd_cli.services.governance_generate_handlers.render_generate_table"
                )
            )
            mock_instr = stack.enter_context(
                patch(
                    "sdd_cli.services.governance_generate_handlers.write_instruction_files_safe"
                )
            )
            mock_prompt = stack.enter_context(
                patch(
                    "sdd_cli.services.governance_generate_handlers.write_prompt_commands_safe"
                )
            )
            mock_adapters = stack.enter_context(
                patch(
                    "sdd_cli.services.governance_generate_handlers.generate_adapters_safe"
                )
            )
            generate_artifacts(
                output_dir=str(tmp_path), path="", output_json=False, console=_console()
            )
        mock_table.assert_called_once()
        mock_instr.assert_called_once()
        mock_prompt.assert_called_once()
        mock_adapters.assert_called_once()


class TestRunGenerate:
    def test_non_bootstrap_delegates_to_generate_artifacts(self) -> None:
        with patch(
            "sdd_cli.services.governance_generate_handlers.generate_artifacts"
        ) as mock_gen:
            run_generate(
                output_dir="/out",
                path="",
                full_bootstrap=False,
                key_id="dev-01",
                profile="client",
                output_json=False,
                console=_console(),
            )
        mock_gen.assert_called_once()

    def test_invalid_kwargs_are_coerced_to_defaults(self) -> None:
        """Non-bool/non-str kwargs fall back to safe defaults (non-bootstrap path)."""
        with patch(
            "sdd_cli.services.governance_generate_handlers.generate_artifacts"
        ) as mock_gen:
            run_generate(
                output_dir="/out",
                path="",
                full_bootstrap="not-a-bool",
                key_id=123,
                profile=None,
                output_json=False,
                console=_console(),
            )
        mock_gen.assert_called_once()

    def test_full_bootstrap_runs_full_sequence(self) -> None:
        compile_fn = MagicMock()
        keygen_fn = MagicMock()
        sign_fn = MagicMock()
        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.generate_artifacts"
            ) as mock_gen,
            patch(
                "sdd_cli.services.governance_generate_handlers.run_bootstrap_signing"
            ) as mock_sign,
            patch(
                "sdd_cli.services.governance_generate_handlers.complete_bootstrap_handshake"
            ) as mock_handshake,
        ):
            run_generate(
                output_dir="/out",
                path="",
                full_bootstrap=True,
                key_id="dev-01",
                profile="client",
                output_json=False,
                console=_console(),
                compile_fn=compile_fn,
                keygen_fn=keygen_fn,
                sign_fn=sign_fn,
            )
        compile_fn.assert_called_once_with(profile="client")
        mock_gen.assert_called_once()
        mock_sign.assert_called_once_with(
            "dev-01", keygen_fn=keygen_fn, sign_fn=sign_fn
        )
        mock_handshake.assert_called_once()

    def test_full_bootstrap_without_compile_fn(self) -> None:
        with (
            patch("sdd_cli.services.governance_generate_handlers.generate_artifacts"),
            patch(
                "sdd_cli.services.governance_generate_handlers.run_bootstrap_signing"
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.complete_bootstrap_handshake"
            ),
        ):
            run_generate(
                output_dir="/out",
                path="",
                full_bootstrap=True,
                key_id="dev-01",
                profile="client",
                output_json=True,
                console=_console(),
            )
