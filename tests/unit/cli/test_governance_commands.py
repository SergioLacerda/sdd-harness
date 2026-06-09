"""Unit tests for sdd_cli.commands.governance helper functions."""

from __future__ import annotations

import configparser
import contextlib
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestCheckFilesAccessible:
    def test_delegates_to_validate_governance_path(self) -> None:
        from sdd_cli.commands.governance import _check_files_accessible

        with patch("sdd_cli.utils.loader.validate_governance_path") as mock_validate:
            mock_validate.return_value = True
            result = _check_files_accessible("runtime/compiled")
            assert result is True
            mock_validate.assert_called_once_with("runtime/compiled")

    def test_returns_false_when_invalid(self) -> None:
        from sdd_cli.commands.governance import _check_files_accessible

        with patch("sdd_cli.utils.loader.validate_governance_path") as mock_validate:
            mock_validate.return_value = False
            result = _check_files_accessible("nonexistent/path")
            assert result is False


class TestCheckFingerprintsValid:
    def test_returns_true_when_both_fingerprints_present(self) -> None:
        from sdd_cli.commands.governance import _check_fingerprints_valid

        config = {
            "core_fingerprint": "abc123",
            "client_fingerprint": "def456",
        }
        result = _check_fingerprints_valid(config)
        assert result is True

    def test_returns_false_when_config_is_none(self) -> None:
        from sdd_cli.commands.governance import _check_fingerprints_valid

        result = _check_fingerprints_valid(None)
        assert result is False

    def test_returns_false_when_core_fingerprint_missing(self) -> None:
        from sdd_cli.commands.governance import _check_fingerprints_valid

        config = {"client_fingerprint": "def456"}
        result = _check_fingerprints_valid(config)
        assert result is False

    def test_returns_false_when_client_fingerprint_missing(self) -> None:
        from sdd_cli.commands.governance import _check_fingerprints_valid

        config = {"core_fingerprint": "abc123"}
        result = _check_fingerprints_valid(config)
        assert result is False


class TestCheckNoConflicts:
    def test_returns_false_when_config_is_none(self) -> None:
        from sdd_cli.commands.governance import _check_no_conflicts

        result = _check_no_conflicts(None)
        assert result is False

    def test_returns_true_when_fingerprints_differ(self) -> None:
        from sdd_cli.commands.governance import _check_no_conflicts

        config = {
            "core_fingerprint": "abc123",
            "client_fingerprint": "def456",
        }
        result = _check_no_conflicts(config)
        assert result is True

    def test_returns_false_when_fingerprints_same(self) -> None:
        from sdd_cli.commands.governance import _check_no_conflicts

        config = {
            "core_fingerprint": "abc123",
            "client_fingerprint": "abc123",
        }
        result = _check_no_conflicts(config)
        assert result is False


class TestRunCompilation:
    def test_raises_exit_when_pipeline_fails(self) -> None:
        import typer

        from sdd_cli.commands.governance import _run_compilation

        mock_orchestrator = MagicMock()
        mock_orchestrator.run_full_pipeline.return_value = {
            "full_pipeline_success": False
        }

        with (
            patch(
                "sdd_core.governance_orchestrator.GovernanceOrchestrator",
                return_value=mock_orchestrator,
            ),
            pytest.raises(typer.Exit),
        ):
            _run_compilation()

    def test_returns_result_on_success(self) -> None:
        from sdd_cli.commands.governance import _run_compilation

        mock_orchestrator = MagicMock()
        mock_orchestrator.run_full_pipeline.return_value = {
            "full_pipeline_success": True,
            "phase_1": {},
        }

        with patch(
            "sdd_core.governance_orchestrator.GovernanceOrchestrator",
            return_value=mock_orchestrator,
        ):
            result = _run_compilation()
            assert result["full_pipeline_success"] is True


class TestUpdateProfileHash:
    def test_does_nothing_when_fingerprint_empty(self) -> None:
        from sdd_cli.commands.governance import _update_profile_hash

        # Should not raise even with empty fingerprint
        _update_profile_hash("")

    def test_updates_profile_when_present(self, tmp_path: Path) -> None:
        from sdd_cli.commands.governance import _update_profile_hash

        # Create a mock profile
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        profile_path = sdd_dir / "profile"
        parser = configparser.ConfigParser()
        parser["sdd"] = {"type": "client", "core_hash": "old_hash_12345678"}
        with open(profile_path, "w", encoding="utf-8") as f:
            parser.write(f)

        with patch(
            "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            _update_profile_hash("new_fingerprint_abc123")

        # Read back and check
        parser2 = configparser.ConfigParser()
        parser2.read(profile_path)
        # The hash should be updated (to first 16 chars of new_fingerprint_abc123)
        assert parser2["sdd"]["core_hash"] == "new_fingerprint_"

    def test_skips_when_workspace_not_found(self) -> None:
        from sdd_cli.commands.governance import _update_profile_hash

        with patch(
            "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
            return_value=None,
        ):
            # Should not raise
            _update_profile_hash("some_fingerprint_12345")

    def test_reads_artifact_fingerprint_when_available(self, tmp_path: Path) -> None:
        from sdd_cli.commands.governance import _update_profile_hash

        # Create .sdd/profile
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        profile_path = sdd_dir / "profile"
        parser = configparser.ConfigParser()
        parser["sdd"] = {"type": "client", "core_hash": "old_hash"}
        with open(profile_path, "w", encoding="utf-8") as f:
            parser.write(f)

        # Create artifact with embedded fingerprint
        artifact_dir = tmp_path / ".sdd" / "compiled"
        artifact_dir.mkdir(parents=True)
        artifact_data = {"items": [], "fingerprint": "artifact_fp_12345678"}
        (artifact_dir / "governance-core.json").write_text(
            json.dumps(artifact_data), encoding="utf-8"
        )

        with patch(
            "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            _update_profile_hash("ignored_fp")

        parser2 = configparser.ConfigParser()
        parser2.read(profile_path)
        assert parser2["sdd"]["core_hash"] == "artifact_fp_1234"


class TestRegenerateSeeds:
    def test_does_not_raise_on_exception(self) -> None:
        from sdd_cli.commands.governance import _regenerate_seeds

        with patch(
            "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
            side_effect=Exception("fail"),
        ):
            # Should catch and not re-raise
            _regenerate_seeds()

    def test_regenerates_when_workspace_found(self, tmp_path: Path) -> None:
        from sdd_cli.commands.governance import _regenerate_seeds

        compiled_dir = tmp_path / ".sdd" / "compiled"
        compiled_dir.mkdir(parents=True)

        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.utils.loader.validate_governance_path",
                return_value=False,
            ),
            patch(
                "sdd_cli.generators.agent_seeds.generate_agent_instruction_files"
            ) as mock_gen,
        ):
            _regenerate_seeds()
            # When validate_governance_path returns False, load_governance_config is not called
            # and generate_agent_instruction_files is still called with {} config
            mock_gen.assert_called_once()

    def test_skips_when_workspace_not_found(self) -> None:
        from sdd_cli.commands.governance import _regenerate_seeds

        with patch(
            "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
            return_value=None,
        ):
            # No workspace → should skip silently
            _regenerate_seeds()

    def test_uses_test_output_dir_when_env_set(self, tmp_path: Path) -> None:
        from sdd_cli.commands.governance import _regenerate_seeds

        compiled_dir = tmp_path / ".sdd" / "compiled"
        compiled_dir.mkdir(parents=True)
        out_dir = tmp_path / "test-output"

        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.utils.loader.validate_governance_path",
                return_value=False,
            ),
            patch.dict(
                "os.environ", {"SDD_TEST_OUTPUT_DIR": str(out_dir)}, clear=False
            ),
            patch(
                "sdd_cli.generators.agent_seeds.generate_agent_instruction_files"
            ) as mock_gen,
        ):
            _regenerate_seeds()
            assert mock_gen.call_count == 1
            assert mock_gen.call_args[0][0] == out_dir


class TestResolveGeneratePath:
    def test_returns_path_when_provided(self) -> None:
        from sdd_cli.commands.governance import _resolve_generate_path

        result = _resolve_generate_path("my/custom/path")
        assert result == "my/custom/path"

    def test_uses_workspace_root_when_no_path(self, tmp_path: Path) -> None:
        from sdd_cli.commands.governance import _resolve_generate_path

        with patch(
            "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
            return_value=tmp_path,
        ):
            result = _resolve_generate_path("")
            assert Path(result) == tmp_path / ".sdd" / "compiled"

    def test_fails_when_no_workspace(self) -> None:
        import typer

        from sdd_cli.commands.governance import _resolve_generate_path

        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=None,
            ),
            pytest.raises(typer.Exit),
        ):
            _resolve_generate_path("")

    def test_raises_exit_when_no_root_found(self) -> None:
        import typer

        from sdd_cli.commands.governance import _resolve_generate_path

        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_workspace_root",
                return_value=None,
            ),
            pytest.raises(typer.Exit),
        ):
            _resolve_generate_path("")


class TestGenerateSeeds:
    def test_returns_seeds_info_and_dir(self, tmp_path: Path) -> None:
        from sdd_cli.commands.governance import _generate_seeds

        mock_seeds = [("copilot", tmp_path / "seed.md", "OK")]
        with patch(
            "sdd_cli.services.governance_generate_handlers.generate_agent_seeds",
            return_value=mock_seeds,
        ):
            seeds_info, seeds_dir = _generate_seeds(str(tmp_path), {})
            assert seeds_info == mock_seeds
            assert ".vscode" in str(seeds_dir)

    def test_raises_os_error_when_vscode_write_fails(self, tmp_path: Path) -> None:
        from sdd_cli.commands.governance import _generate_seeds

        def mock_gen(_seeds_dir: Any, _cfg: Any) -> Any:
            raise OSError("permission denied")

        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.generate_agent_seeds",
                side_effect=mock_gen,
            ),
            pytest.raises(OSError, match="permission denied"),
        ):
            _generate_seeds(str(tmp_path), {})


class TestGenerateCommandBootstrap:
    def test_generate_default_path_uses_artifacts_only(self) -> None:
        from unittest.mock import ANY

        from sdd_cli.commands.governance import generate as governance_generate

        with patch("sdd_cli.commands.governance._generate_artifacts") as mock_generate:
            governance_generate(output_dir=None, path="", full_bootstrap=False)
            mock_generate.assert_called_once_with(
                output_dir=None, path="", output_json=ANY, console=ANY
            )

    def test_generate_full_bootstrap_executes_expected_sequence(self) -> None:
        from unittest.mock import ANY

        from sdd_cli.commands.governance import generate as governance_generate

        with (
            patch("sdd_cli.commands.governance.compile") as mock_compile,
            patch(
                "sdd_cli.commands.governance._generate_artifacts"
            ) as mock_generate_artifacts,
            patch("sdd_cli.commands.governance._run_bootstrap_signing") as mock_signing,
            patch(
                "sdd_cli.commands.governance._complete_bootstrap_handshake"
            ) as mock_handshake,
        ):
            governance_generate(
                output_dir=None,
                path="",
                full_bootstrap=True,
                key_id="dev-01",
            )
            mock_compile.assert_called_once_with(profile="client")
            mock_generate_artifacts.assert_called_once_with(
                output_dir=None, path="", output_json=ANY, console=ANY
            )
            mock_signing.assert_called_once_with("dev-01", keygen_fn=ANY, sign_fn=ANY)
            mock_handshake.assert_called_once_with()


def test_governance_help_does_not_expose_internal_resolve_generate_path() -> None:
    from click.testing import CliRunner

    from sdd_cli.main import app as root_app

    result = CliRunner().invoke(root_app, ["governance", "--help"])
    assert result.exit_code == 0, result.output
    assert "_resolve-generate-path" not in result.output


# ---------------------------------------------------------------------------
# compile() command
# ---------------------------------------------------------------------------


class TestCompileCommand:
    def test_compile_succeeds(self) -> None:
        from sdd_cli.commands.governance import compile as governance_compile

        mock_result = {
            "full_pipeline_success": True,
            "phase_1": {
                "core_fingerprint": "a" * 64,
                "core_item_count": 2,
                "client_item_count": 1,
            },
            "phase_2": {
                "core_msgpack_file": "/out/core.msgpack",
                "client_msgpack_file": "/out/client.msgpack",
            },
        }
        with (
            patch(
                "sdd_cli.commands.governance._run_compilation", return_value=mock_result
            ),
            patch("sdd_cli.commands.governance._update_profile_hash"),
            patch(
                "sdd_cli.commands.governance._resolve_generate_path",
                return_value="runtime/compiled",
            ),
            patch(
                "sdd_cli.commands.governance._check_artifact_consistency",
                return_value=(True, "ok"),
            ),
            patch("sdd_cli.commands.governance._regenerate_seeds"),
        ):
            # Should not raise
            governance_compile()

    def test_compile_reraises_typer_exit(self) -> None:
        import typer

        from sdd_cli.commands.governance import compile as governance_compile

        with (
            patch(
                "sdd_cli.commands.governance._run_compilation",
                side_effect=typer.Exit(1),
            ),
            patch(
                "sdd_cli.commands.governance._resolve_generate_path",
                return_value="runtime/compiled",
            ),
            pytest.raises(typer.Exit),
        ):
            governance_compile()

    def test_compile_raises_exit_on_exception(self) -> None:
        import typer

        from sdd_cli.commands.governance import compile as governance_compile

        with (
            patch(
                "sdd_cli.commands.governance._run_compilation",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "sdd_cli.commands.governance._resolve_generate_path",
                return_value="runtime/compiled",
            ),
            pytest.raises(typer.Exit),
        ):
            governance_compile()

    def test_compile_fails_when_consistency_check_fails(self) -> None:
        import typer

        from sdd_cli.commands.governance import compile as governance_compile

        mock_result = {
            "full_pipeline_success": True,
            "phase_1": {
                "core_fingerprint": "a" * 64,
                "core_item_count": 2,
                "client_item_count": 1,
            },
            "phase_2": {
                "core_msgpack_file": "/out/core.msgpack",
                "client_msgpack_file": "/out/client.msgpack",
            },
        }
        with (
            patch(
                "sdd_cli.commands.governance._run_compilation", return_value=mock_result
            ),
            patch("sdd_cli.commands.governance._update_profile_hash"),
            patch(
                "sdd_cli.commands.governance._resolve_generate_path",
                return_value="runtime/compiled",
            ),
            patch(
                "sdd_cli.commands.governance._check_artifact_consistency",
                return_value=(False, "core fingerprint mismatch"),
            ),
            pytest.raises(typer.Exit),
        ):
            governance_compile()


# ---------------------------------------------------------------------------
# load() command
# ---------------------------------------------------------------------------


class TestLoadCommand:
    def test_load_succeeds(self) -> None:
        from sdd_cli.commands.governance import load as governance_load

        mock_config = {"core_fingerprint": "abc", "client_fingerprint": "def"}
        mock_summary = {"status": "OK", "items": "3"}
        with (
            patch(
                "sdd_cli.commands.governance.validate_governance_path",
                return_value=True,
            ),
            patch(
                "sdd_cli.commands.governance.load_governance_config",
                return_value=mock_config,
            ),
            patch(
                "sdd_cli.commands.governance.get_governance_summary",
                return_value=mock_summary,
            ),
        ):
            governance_load(path="some/path")

    def test_load_raises_exit_when_invalid_path(self) -> None:
        import typer

        from sdd_cli.commands.governance import load as governance_load

        with (
            patch(
                "sdd_cli.commands.governance.validate_governance_path",
                return_value=False,
            ),
            pytest.raises(typer.Exit),
        ):
            governance_load(path="bad/path")

    def test_load_raises_exit_on_file_not_found(self) -> None:
        import typer

        from sdd_cli.commands.governance import load as governance_load

        with (
            patch(
                "sdd_cli.commands.governance.validate_governance_path",
                return_value=True,
            ),
            patch(
                "sdd_cli.commands.governance.load_governance_config",
                side_effect=FileNotFoundError("missing"),
            ),
            pytest.raises(typer.Exit),
        ):
            governance_load(path="some/path")

    def test_load_raises_exit_on_exception(self) -> None:
        import typer

        from sdd_cli.commands.governance import load as governance_load

        with (
            patch(
                "sdd_cli.commands.governance.validate_governance_path",
                return_value=True,
            ),
            patch(
                "sdd_cli.commands.governance.load_governance_config",
                side_effect=RuntimeError("fail"),
            ),
            pytest.raises(typer.Exit),
        ):
            governance_load(path="some/path")


# ---------------------------------------------------------------------------
# validate() command
# ---------------------------------------------------------------------------


class TestValidateCommand:
    def test_validate_all_pass(self) -> None:
        from sdd_cli.commands.governance import validate as governance_validate

        mock_config = {"core_fingerprint": "a" * 64, "client_fingerprint": "b" * 64}
        with (
            patch(
                "sdd_cli.commands.governance.validate_governance_path",
                return_value=True,
            ),
            patch(
                "sdd_cli.commands.governance.load_governance_config",
                return_value=mock_config,
            ),
            patch(
                "sdd_cli.commands.governance._check_files_accessible", return_value=True
            ),
            patch(
                "sdd_cli.commands.governance._check_fingerprints_valid",
                return_value=True,
            ),
            patch("sdd_cli.commands.governance._check_no_conflicts", return_value=True),
            patch(
                "sdd_cli.commands.governance._check_artifact_consistency",
                return_value=(True, "ok"),
            ),
        ):
            # Should not raise
            governance_validate(path="runtime/compiled", signature_mode="off")

    def test_validate_raises_exit_when_checks_fail(self) -> None:
        import typer

        from sdd_cli.commands.governance import validate as governance_validate

        with (
            patch(
                "sdd_cli.commands.governance.validate_governance_path",
                return_value=False,
            ),
            patch(
                "sdd_cli.commands.governance._check_files_accessible",
                return_value=False,
            ),
            patch(
                "sdd_cli.commands.governance._check_fingerprints_valid",
                return_value=False,
            ),
            patch(
                "sdd_cli.commands.governance._check_no_conflicts", return_value=False
            ),
            patch(
                "sdd_cli.commands.governance._check_artifact_consistency",
                return_value=(False, "mismatch"),
            ),
            pytest.raises(typer.Exit),
        ):
            governance_validate(path="bad/path", signature_mode="off")

    def test_validate_raises_exit_on_exception(self) -> None:
        import typer

        from sdd_cli.commands.governance import validate as governance_validate

        with (
            patch(
                "sdd_cli.commands.governance.validate_governance_path",
                side_effect=RuntimeError("boom"),
            ),
            pytest.raises(typer.Exit),
        ):
            governance_validate(path="some/path", signature_mode="off")


class TestArtifactConsistency:
    def test_detects_malformed_title_pattern(self) -> None:
        from sdd_cli.commands.governance import _has_malformed_titles

        assert _has_malformed_titles([{"id": "M015", "title": "- Status: Accepted"}])

    def test_accepts_regular_titles(self) -> None:
        from sdd_cli.commands.governance import _has_malformed_titles

        assert not _has_malformed_titles(
            [{"id": "M001", "title": "Clean Architecture"}]
        )


# ---------------------------------------------------------------------------
# generate() command
# ---------------------------------------------------------------------------


class TestGenerateCommandSeedsFlow:
    def test_generate_succeeds(self, tmp_path: Path) -> None:
        from sdd_cli.commands.governance import generate as governance_generate

        mock_config = {"items": [{"id": "M001"}]}
        mock_seeds = [("copilot", tmp_path / "seed.md", "OK")]
        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_generate_path",
                return_value="some/path",
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.validate_governance_path",
                return_value=True,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.load_governance_config",
                return_value=mock_config,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.generate_seeds",
                return_value=(mock_seeds, tmp_path / ".vscode" / "agents"),
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.run_generate_phases",
                return_value=(True, True, True),
            ),
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_output_base",
                return_value=tmp_path,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.write_instruction_files_safe",
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.write_prompt_commands_safe",
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.generate_adapters_safe",
            ),
        ):
            governance_generate(output_dir=str(tmp_path), path="some/path")

    def test_generate_raises_exit_when_invalid_path(self) -> None:
        import typer

        from sdd_cli.commands.governance import generate as governance_generate

        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_generate_path",
                return_value="bad/path",
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.validate_governance_path",
                return_value=False,
            ),
            pytest.raises(typer.Exit),
        ):
            governance_generate(output_dir=".", path="bad/path")

    def test_generate_raises_exit_when_no_items(self) -> None:
        import typer

        from sdd_cli.commands.governance import generate as governance_generate

        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_generate_path",
                return_value="some/path",
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.validate_governance_path",
                return_value=True,
            ),
            patch(
                "sdd_cli.services.governance_generate_handlers.load_governance_config",
                return_value={"items": []},
            ),
            pytest.raises(typer.Exit),
        ):
            governance_generate(output_dir=".", path="some/path")

    def test_generate_raises_exit_on_exception(self) -> None:
        import typer

        from sdd_cli.commands.governance import generate as governance_generate

        with (
            patch(
                "sdd_cli.services.governance_generate_handlers.resolve_generate_path",
                side_effect=RuntimeError("fail"),
            ),
            pytest.raises(typer.Exit),
        ):
            governance_generate(output_dir=".", path="")

    def test_resolve_output_base_redirects_workspace_root_in_test_mode(
        self, tmp_path: Path
    ) -> None:
        from sdd_cli.commands.governance import _resolve_output_base

        ws_root = tmp_path / "ws"
        ws_root.mkdir(parents=True)
        redirected = tmp_path / "redirected"

        with (
            patch(
                "sdd_cli.services.governance_compile_handlers.resolve_workspace_root",
                return_value=ws_root,
            ),
            patch.dict(
                "os.environ", {"SDD_TEST_OUTPUT_DIR": str(redirected)}, clear=False
            ),
        ):
            resolved = _resolve_output_base(ws_root)
            assert resolved == redirected.resolve()


# ---------------------------------------------------------------------------
# score() command
# ---------------------------------------------------------------------------


class TestScoreCommand:
    def _make_ahp_report(self, confidence: float = 80.0) -> MagicMock:
        report = MagicMock()
        report.confidence = confidence
        return report

    def test_score_raises_exit_when_no_workspace(self) -> None:
        import typer

        from sdd_cli.commands.governance import score as governance_score

        with (
            patch(
                "sdd_cli.commands.governance.resolve_workspace_root", return_value=None
            ),
            pytest.raises(typer.Exit),
        ):
            governance_score(verbose=False, threshold=80)

    def test_score_passes_when_all_checks_pass(self, tmp_path: Path) -> None:
        from sdd_cli.commands.governance import score as governance_score

        # Create a valid profile + artifact
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        import configparser

        parser = configparser.ConfigParser()
        parser["sdd"] = {"type": "client", "core_hash": "abc123"}
        with open(sdd_dir / "profile", "w", encoding="utf-8") as f:
            parser.write(f)

        artifact_dir = tmp_path / ".sdd" / "compiled"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "governance-core.json").write_text(
            json.dumps({"fingerprint": "abc123def4567890"}), encoding="utf-8"
        )

        mock_profile = MagicMock()
        mock_profile.core_hash = "abc123def4567890"[:16]
        mock_profile.is_client = True
        mock_profile.is_master = False

        mock_ahp_report = self._make_ahp_report(confidence=90.0)
        mock_ahp = MagicMock()
        mock_ahp.validate.return_value = ("HEALTHY", mock_ahp_report)

        with (
            patch(
                "sdd_cli.commands.governance.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_core.utils.environment.resolve_profile", return_value=mock_profile
            ),
            patch(
                "sdd_core.governance.handshake.AgentHandshakeProtocol",
                return_value=mock_ahp,
            ),
        ):
            # Should not raise (score >= threshold)
            governance_score(verbose=False, threshold=80)

    def test_score_raises_exit_when_below_threshold(self, tmp_path: Path) -> None:
        import typer

        from sdd_cli.commands.governance import score as governance_score
        from sdd_core.utils.environment import WorkspaceNotInitializedError

        mock_ahp_report = self._make_ahp_report(confidence=10.0)
        mock_ahp = MagicMock()
        mock_ahp.validate.return_value = ("DEGRADED", mock_ahp_report)

        with (
            patch(
                "sdd_cli.commands.governance.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_core.utils.environment.resolve_profile",
                side_effect=WorkspaceNotInitializedError(tmp_path),
            ),
            patch(
                "sdd_core.governance.handshake.AgentHandshakeProtocol",
                return_value=mock_ahp,
            ),
            pytest.raises(typer.Exit),
        ):
            governance_score(verbose=False, threshold=80)

    def test_score_verbose_does_not_raise(self, tmp_path: Path) -> None:
        from sdd_cli.commands.governance import score as governance_score
        from sdd_core.utils.environment import WorkspaceNotInitializedError

        mock_ahp_report = self._make_ahp_report(confidence=100.0)
        mock_ahp = MagicMock()
        mock_ahp.validate.return_value = ("HEALTHY", mock_ahp_report)

        with (
            patch(
                "sdd_cli.commands.governance.resolve_workspace_root",
                return_value=tmp_path,
            ),
            patch(
                "sdd_core.utils.environment.resolve_profile",
                side_effect=WorkspaceNotInitializedError(tmp_path),
            ),
            patch(
                "sdd_core.governance.handshake.AgentHandshakeProtocol",
                return_value=mock_ahp,
            ),
            contextlib.suppress(SystemExit),
        ):
            # Low score but verbose flag should show table before raising
            governance_score(verbose=True, threshold=0)
