"""Unit tests for sdd_cli.services.skills_resolver."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from sdd_cli.services.skills_resolver import (
    _generate_adapters,
    _read_registry_ids,
    _reconcile_root_seed_artifacts,
    handle_adapter_error,
    run_full_bootstrap,
    run_reconcile,
    validate_and_load_governance,
)


class TestReadRegistryIds:
    def test_raises_on_non_list_value(self, tmp_path: Path) -> None:
        reg = tmp_path / "registry.json"
        reg.write_text(json.dumps({"commands": "not-a-list"}), encoding="utf-8")
        with pytest.raises(ValueError, match=r"invalid registry format for "):
            _read_registry_ids(reg, "commands", "id")

    def test_skips_non_dict_rows(self, tmp_path: Path) -> None:
        reg = tmp_path / "registry.json"
        reg.write_text(
            json.dumps({"commands": ["string-row", {"id": "sdd-ask"}]}),
            encoding="utf-8",
        )
        result = _read_registry_ids(reg, "commands", "id")
        assert result == ["sdd-ask"]


class TestReconcileRootSeedArtifacts:
    def test_prunes_stale_files(self, tmp_path: Path) -> None:
        commands_registry = tmp_path / ".sdd" / "commands"
        skills_registry = tmp_path / ".sdd" / "skills"
        commands_registry.mkdir(parents=True, exist_ok=True)
        skills_registry.mkdir(parents=True, exist_ok=True)
        (commands_registry / "registry.json").write_text(
            json.dumps(
                {
                    "commands": [
                        {"id": "sdd-ask"},
                        {"id": "sdd-pipeline"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        (skills_registry / "registry.json").write_text(
            json.dumps({"skills": [{"name": "sdd-ask"}, {"name": "sdd-diagnose"}]}),
            encoding="utf-8",
        )

        prompts = tmp_path / ".github" / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        (prompts / "sdd-ask.prompt.md").write_text("ok", encoding="utf-8")
        (prompts / "sdd-legacy.prompt.md").write_text("stale", encoding="utf-8")

        codex_skills = tmp_path / ".codex" / "skills"
        codex_skills.mkdir(parents=True, exist_ok=True)
        (codex_skills / "sdd-pipeline.prompt.md").write_text("ok", encoding="utf-8")
        (codex_skills / "sdd-legacy.prompt.md").write_text("stale", encoding="utf-8")

        claude_cmds = tmp_path / ".claude" / "commands"
        claude_cmds.mkdir(parents=True, exist_ok=True)
        (claude_cmds / "sdd-ask.md").write_text("ok", encoding="utf-8")
        (claude_cmds / "sdd-legacy.md").write_text("stale", encoding="utf-8")

        gemini_skills = tmp_path / ".gemini" / "antigravity" / "skills"
        gemini_skills.mkdir(parents=True, exist_ok=True)
        (gemini_skills / "sdd-ask").mkdir()
        (gemini_skills / "sdd-governance").mkdir()
        (gemini_skills / "sdd-legacy").mkdir()
        stats = _reconcile_root_seed_artifacts(tmp_path)

        assert stats["deleted"] == 4
        assert (prompts / "sdd-legacy.prompt.md").exists() is False
        assert (codex_skills / "sdd-legacy.prompt.md").exists() is False
        assert (claude_cmds / "sdd-legacy.md").exists() is False
        assert (gemini_skills / "sdd-legacy").exists() is False
        assert (gemini_skills / "sdd-governance").exists() is True

    def test_dry_run_does_not_delete(self, tmp_path: Path) -> None:
        commands_registry = tmp_path / ".sdd" / "commands"
        skills_registry = tmp_path / ".sdd" / "skills"
        commands_registry.mkdir(parents=True, exist_ok=True)
        skills_registry.mkdir(parents=True, exist_ok=True)
        (commands_registry / "registry.json").write_text(
            json.dumps({"commands": [{"id": "sdd-ask"}]}),
            encoding="utf-8",
        )
        (skills_registry / "registry.json").write_text(
            json.dumps({"skills": [{"name": "sdd-ask"}]}),
            encoding="utf-8",
        )
        prompts = tmp_path / ".github" / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        stale = prompts / "sdd-legacy.prompt.md"
        stale.write_text("stale", encoding="utf-8")

        stats = _reconcile_root_seed_artifacts(tmp_path, dry_run=True)
        assert stats["would_delete"] == 1
        assert stats["deleted"] == 0
        assert stale.exists() is True

    def test_fails_without_registries(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _reconcile_root_seed_artifacts(tmp_path)


class TestGenerateAdapters:
    def test_returns_zero_on_import_error(self) -> None:
        with patch(
            "sdd_adapters.adapter_generator.AdapterGenerator",
            side_effect=ImportError("no adapters"),
        ):
            count, err = _generate_adapters(Path("/tmp"))
        assert count == 0
        assert err is not None

    def test_returns_count_on_success(self, tmp_path: Path) -> None:
        with patch("sdd_adapters.adapter_generator.AdapterGenerator") as mock_cls:
            mock_cls.return_value.generate.return_value = [1, 2, 3]
            count, err = _generate_adapters(tmp_path)
        assert count == 3
        assert err is None


class TestHandleAdapterError:
    def test_text_mode_prints_error_and_exits(self) -> None:
        mock_emit = MagicMock()
        with pytest.raises(typer.Exit) as exc_info:
            handle_adapter_error("template error", output_json=False, emit_fn=mock_emit)
        assert exc_info.value.exit_code == 1
        mock_emit.assert_not_called()

    def test_json_mode_emits_error_and_exits(self) -> None:
        mock_emit = MagicMock()
        with pytest.raises(typer.Exit) as exc_info:
            handle_adapter_error("template error", output_json=True, emit_fn=mock_emit)
        assert exc_info.value.exit_code == 1
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "adapter_generation_failed"


class TestValidateAndLoadGovernance:
    def test_text_mode_exits_on_invalid_path(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "sdd_cli.services.skills_resolver.validate_governance_path",
                return_value=False,
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            validate_and_load_governance(
                tmp_path / ".sdd" / "compiled",
                output_json=False,
                emit_fn=mock_emit,
            )
        assert exc_info.value.exit_code == 1
        mock_emit.assert_not_called()

    def test_json_mode_exits_on_invalid_path(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "sdd_cli.services.skills_resolver.validate_governance_path",
                return_value=False,
            ),
            pytest.raises(typer.Exit),
        ):
            validate_and_load_governance(
                tmp_path / ".sdd" / "compiled",
                output_json=True,
                emit_fn=mock_emit,
            )
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "missing_governance_artifacts"

    def test_text_mode_exits_on_empty_items(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "sdd_cli.services.skills_resolver.validate_governance_path",
                return_value=True,
            ),
            patch(
                "sdd_cli.services.skills_resolver.load_governance_config",
                return_value={"items": []},
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            validate_and_load_governance(
                tmp_path / ".sdd" / "compiled",
                output_json=False,
                emit_fn=mock_emit,
            )
        assert exc_info.value.exit_code == 1

    def test_json_mode_exits_on_empty_items(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "sdd_cli.services.skills_resolver.validate_governance_path",
                return_value=True,
            ),
            patch(
                "sdd_cli.services.skills_resolver.load_governance_config",
                return_value={"items": []},
            ),
            pytest.raises(typer.Exit),
        ):
            validate_and_load_governance(
                tmp_path / ".sdd" / "compiled",
                output_json=True,
                emit_fn=mock_emit,
            )
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "missing_governance_items"


class TestRunReconcile:
    def test_text_mode_exits_on_exception(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "sdd_cli.services.skills_resolver._reconcile_root_seed_artifacts",
                side_effect=FileNotFoundError("no registry"),
            ),
            pytest.raises(typer.Exit) as exc_info,
        ):
            run_reconcile(tmp_path, dry_run=False, output_json=False, emit_fn=mock_emit)
        assert exc_info.value.exit_code == 1
        mock_emit.assert_not_called()

    def test_json_mode_exits_on_exception(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        with (
            patch(
                "sdd_cli.services.skills_resolver._reconcile_root_seed_artifacts",
                side_effect=FileNotFoundError("no registry"),
            ),
            pytest.raises(typer.Exit),
        ):
            run_reconcile(tmp_path, dry_run=False, output_json=True, emit_fn=mock_emit)
        call_kwargs = mock_emit.call_args[1]
        assert call_kwargs["error_code"] == "seed_reconciliation_failed"


class TestRunFullBootstrap:
    def _make_reconcile_summary(self) -> MagicMock:
        summary = MagicMock()
        summary.as_json.return_value = {}
        summary.commands = {"added": 2, "removed": 0}
        summary.skills = {"added": 3, "removed": 0}
        return summary

    def test_text_mode_prints_completion_summary(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        reconcile_summary = self._make_reconcile_summary()

        with (
            patch(
                "sdd_cli.services.skills_resolver.validate_and_load_governance",
                return_value={"items": [{}]},
            ),
            patch(
                "sdd_cli.services.skills_resolver.generate_agent_seeds",
                return_value=[1, 2],
            ),
            patch("sdd_cli.services.skills_resolver.generate_agent_instruction_files"),
            patch("sdd_cli.services.skills_resolver.generate_agent_prompt_commands"),
            patch(
                "sdd_cli.services.skills_resolver.generate_skills_registry",
                return_value={"skill_count": 5},
            ),
            patch(
                "sdd_cli.services.skills_resolver.generate_commands_registry",
                return_value={"command_count": 3},
            ),
            patch(
                "sdd_cli.services.skills_resolver.reconcile_registries",
                return_value=reconcile_summary,
            ),
            patch(
                "sdd_cli.services.skills_resolver.generate_skill_index",
                return_value={"skill_count": 5},
            ),
            patch(
                "sdd_cli.services.skills_resolver.generate_cli_commands_index",
                return_value={"command_count": 3},
            ),
            patch(
                "sdd_cli.services.skills_resolver._generate_adapters",
                return_value=(2, None),
            ),
        ):
            run_full_bootstrap(
                tmp_path,
                regenerate_seeds=False,
                dry_run=False,
                output_json=False,
                emit_fn=mock_emit,
            )
        mock_emit.assert_not_called()

    def test_text_mode_prints_deleted_seeds_on_regenerate(self, tmp_path: Path) -> None:
        mock_emit = MagicMock()
        reconcile_summary = self._make_reconcile_summary()

        with (
            patch(
                "sdd_cli.services.skills_resolver.validate_and_load_governance",
                return_value={"items": [{}]},
            ),
            patch(
                "sdd_cli.services.skills_resolver.generate_agent_seeds",
                return_value=[],
            ),
            patch("sdd_cli.services.skills_resolver.generate_agent_instruction_files"),
            patch("sdd_cli.services.skills_resolver.generate_agent_prompt_commands"),
            patch(
                "sdd_cli.services.skills_resolver.generate_skills_registry",
                return_value={"skill_count": 0},
            ),
            patch(
                "sdd_cli.services.skills_resolver.generate_commands_registry",
                return_value={"command_count": 0},
            ),
            patch(
                "sdd_cli.services.skills_resolver.reconcile_registries",
                return_value=reconcile_summary,
            ),
            patch(
                "sdd_cli.services.skills_resolver.generate_skill_index",
                return_value={"skill_count": 0},
            ),
            patch(
                "sdd_cli.services.skills_resolver.generate_cli_commands_index",
                return_value={"command_count": 0},
            ),
            patch(
                "sdd_cli.services.skills_resolver._generate_adapters",
                return_value=(0, None),
            ),
            patch(
                "sdd_cli.services.skills_resolver.run_reconcile",
                return_value=(3, 3),
            ),
        ):
            run_full_bootstrap(
                tmp_path,
                regenerate_seeds=True,
                dry_run=False,
                output_json=False,
                emit_fn=mock_emit,
            )
        mock_emit.assert_not_called()
