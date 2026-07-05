"""Tests for sdd_cli.services.governance_compile_handlers — profile hash and seed regen."""

from __future__ import annotations

import configparser
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from sdd_cli.services._governance_compile_support import (
    sync_workspace_metadata_from_config,
)
from sdd_cli.services.governance_compile_handlers import (
    regenerate_seeds,
    update_profile_hash,
)


def _console() -> Console:
    return Console(file=io.StringIO(), width=120)


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
            "sdd_cli.services.governance_compile_telemetry.resolve_workspace_root",
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
                "sdd_cli.services.governance_compile_telemetry.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch("sdd_cli.utils.loader.validate_governance_path", return_value=True),
            patch(
                "sdd_cli.utils.loader.load_governance_config",
                return_value={
                    "core_fingerprint": "abcdef0123456789",
                    "items": [
                        {
                            "id": "M001",
                            "type": "MANDATE",
                            "title": "Clean Architecture",
                        }
                    ],
                },
            ),
            patch(
                "sdd_cli.generators.agent_seeds.generate_agent_instruction_files"
            ) as mock_gen_instr,
            patch(
                "sdd_wizard.contracts.generate_agent_instructions_from_config",
                return_value=True,
            ) as mock_gen_wizard,
            patch(
                "sdd_wizard.contracts.generate_root_bootstrap_from_config",
                return_value=True,
            ) as mock_gen_root,
        ):
            regenerate_seeds(console=console)

        mock_gen_instr.assert_called_once()
        mock_gen_wizard.assert_called_once()
        mock_gen_root.assert_called_once()
        output = console.file.getvalue()
        assert ".sdd/metadata.json synchronized" in output
        assert "Agent instruction files regenerated" in output
        assert ".sdd/agent-instructions.md regenerated" in output
        assert "Root bootstrap files regenerated" in output

    def test_invalid_governance_path_uses_empty_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_SKIP_SEED_REGEN", raising=False)
        console = _console()
        with (
            patch(
                "sdd_cli.services.governance_compile_telemetry.resolve_workspace_root",
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
            patch(
                "sdd_wizard.contracts.generate_root_bootstrap_from_config",
                return_value=True,
            ),
        ):
            regenerate_seeds(console=console)

        args, _ = mock_gen_instr.call_args
        assert args[1] == {}

    def test_sync_workspace_metadata_from_config_uses_compiled_fingerprint(
        self, tmp_path: Path
    ) -> None:
        metadata_path = tmp_path / ".sdd" / "metadata.json"
        metadata_path.parent.mkdir(parents=True)
        metadata_path.write_text(
            json.dumps(
                {
                    "version": "3.0",
                    "language_context": {"preferred_chat_language": "pt-BR"},
                    "mandates_count": 1,
                    "fingerprints": {"combined": "old"},
                    "mandates": {"M000": "Old"},
                }
            ),
            encoding="utf-8",
        )

        config = {
            "core_fingerprint": "1234567890abcdef9999",
            "items": [
                {"id": "M001", "type": "MANDATE", "title": "Clean Architecture"},
                {"id": "M002", "type": "MANDATE", "title": "TDD"},
                {"id": "G001", "type": "GUIDELINE", "title": "Style"},
            ],
        }

        assert sync_workspace_metadata_from_config(tmp_path, config) is True
        synced = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert synced["governance_fingerprint"] == "1234567890abcdef"
        assert synced["fingerprints"]["combined"] == "1234567890abcdef"
        assert synced["mandates_count"] == 2
        assert synced["guidelines_count"] == 1
        assert synced["mandates"] == {"M001": "Clean Architecture", "M002": "TDD"}
        assert synced["language_context"] == {"preferred_chat_language": "pt-BR"}

    def test_wizard_import_error_prints_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SDD_SKIP_SEED_REGEN", raising=False)
        console = _console()
        with (
            patch(
                "sdd_cli.services.governance_compile_telemetry.resolve_workspace_root",
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
                "sdd_cli.services.governance_compile_telemetry.resolve_workspace_root",
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
