"""Unit tests for sdd_wizard.src.interactive_mode.InteractiveWizard (non-stdin methods)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_wizard(tmp_path: Path) -> Any:
    from sdd_wizard.src.interactive_mode import InteractiveWizard

    mock_paths = {
        "root": tmp_path,
        "client_build": tmp_path / "generated" / "client" / "build",
        "client_compiled": tmp_path / "generated" / "client" / "compiled",
        "master_compiled": tmp_path / "generated" / "master" / "compiled",
        "client_context": tmp_path / "generated" / "client" / "context",
    }
    with patch(
        "sdd_wizard.src.interactive_mode.get_sdd_paths", return_value=mock_paths
    ):
        wizard = InteractiveWizard(
            repo_root=tmp_path,
            prompter=lambda prompt: input(prompt),  # noqa: PLC3002  # lgtm[py/unnecessary-lambda]
        )
    return wizard


class TestInteractiveWizardInit:
    def test_creates_without_error(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        assert wizard is not None

    def test_has_config_dict(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        assert isinstance(wizard.config, dict)


class TestPrintHeader:
    def test_prints_title(self, tmp_path: Path, capsys: Any) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.print_header("Test Title")
        captured = capsys.readouterr()
        assert "Test Title" in captured.out

    def test_prints_custom_icon(self, tmp_path: Path, capsys: Any) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.print_header("My Title", icon="★")
        captured = capsys.readouterr()
        assert "★" in captured.out


class TestSaveConfig:
    def test_saves_config_to_file(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        config = {"language": "Python", "adoption_level": "FULL"}
        path = wizard.save_config(config)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["language"] == "Python"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        config = {"key": "value"}
        path = wizard.save_config(config)
        assert path.parent.exists()

    def test_returns_path(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        path = wizard.save_config({})
        assert isinstance(path, Path)


class TestDocsMetaBootstrap:
    def test_docs_meta_ready_true_when_files_exist(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        docs_meta = wizard.client_build_dir / "docs-meta"
        docs_meta.mkdir(parents=True, exist_ok=True)
        (docs_meta / "mandate.spec").write_text("mandate", encoding="utf-8")
        (docs_meta / "guidelines.dsl").write_text("guidelines", encoding="utf-8")
        assert wizard._docs_meta_ready() is True

    def test_ensure_docs_meta_runs_bootstrap_when_missing(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        docs_meta = wizard.client_build_dir / "docs-meta"
        docs_meta.mkdir(parents=True, exist_ok=True)

        def _fake_run(*args: Any, **kwargs: Any) -> Any:
            (docs_meta / "mandate.spec").write_text("mandate", encoding="utf-8")
            (docs_meta / "guidelines.dsl").write_text("guidelines", encoding="utf-8")
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = ""
            mock.stderr = ""
            return mock

        with patch("sdd_wizard.src.interactive_mode.SafeProcessRunner") as MockRunner:
            MockRunner.return_value.run.side_effect = _fake_run
            ok, reason = wizard._ensure_docs_meta_ready()

        assert ok is True
        assert reason == ""

    def test_ensure_docs_meta_returns_error_on_bootstrap_failure(
        self, tmp_path: Path
    ) -> None:
        wizard = _make_wizard(tmp_path)
        failed = MagicMock()
        failed.returncode = 1
        failed.stdout = ""
        failed.stderr = "boom"
        with patch("sdd_wizard.src.interactive_mode.SafeProcessRunner") as MockRunner:
            MockRunner.return_value.run.return_value = failed
            ok, reason = wizard._ensure_docs_meta_ready()
        assert ok is False
        assert "sdd docs update" in reason


class TestConsolidateFinalTemplate:
    def test_returns_false_when_no_compiled_dir(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        result = wizard._consolidate_final_template()
        assert result["success"] is False

    def test_returns_false_when_compiled_dir_empty(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_compiled_dir.mkdir(parents=True, exist_ok=True)
        result = wizard._consolidate_final_template()
        assert result["success"] is False

    def test_moves_artifacts_to_final_template(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_compiled_dir.mkdir(parents=True, exist_ok=True)
        (wizard.client_compiled_dir / "governance-core.json").write_text(
            "{}", encoding="utf-8"
        )
        result = wizard._consolidate_final_template()
        assert result["success"] is True
        assert (
            wizard.final_template_dir / ".sdd" / "audit" / "governance-core.json"
        ).exists()

    def test_removes_existing_final_template_dir(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_compiled_dir.mkdir(parents=True, exist_ok=True)
        (wizard.client_compiled_dir / "file.txt").write_text(
            "content", encoding="utf-8"
        )
        wizard.final_template_dir.mkdir(parents=True, exist_ok=True)
        (wizard.final_template_dir / "old.txt").write_text("old", encoding="utf-8")

        wizard._consolidate_final_template()
        assert not (wizard.final_template_dir / "old.txt").exists()

    def test_recreates_compiled_dir_after_move(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_compiled_dir.mkdir(parents=True, exist_ok=True)
        (wizard.client_compiled_dir / "file.txt").write_text(
            "content", encoding="utf-8"
        )
        wizard._consolidate_final_template()
        assert wizard.client_compiled_dir.exists()


class TestPhase2ShowInstructions:
    def test_returns_false_when_phase1_dir_missing(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        result = wizard.phase_2_show_instructions()
        assert result["success"] is False

    def test_returns_false_when_no_supported_files(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.phase1_choices_dir.mkdir(parents=True, exist_ok=True)
        # Create a file with unsupported extension
        (wizard.phase1_choices_dir / "data.csv").write_text("a,b,c", encoding="utf-8")
        result = wizard.phase_2_show_instructions()
        assert result["success"] is False

    def test_copies_supported_files_to_phase2_input(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.phase1_choices_dir.mkdir(parents=True, exist_ok=True)
        (wizard.phase1_choices_dir / "mandates.md").write_text(
            "# Mandates", encoding="utf-8"
        )

        # phase_2_show_instructions prints a lot, but we stop at the print of files
        # The function may call input() later — mock it
        with patch("builtins.input", return_value=""):
            wizard.phase_2_show_instructions()

        assert (wizard.phase2_input_dir / "mandates.md").exists()

    def test_detailed_result_includes_copied_files(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.phase1_choices_dir.mkdir(parents=True, exist_ok=True)
        (wizard.phase1_choices_dir / "mandates.md").write_text(
            "# Mandates", encoding="utf-8"
        )
        with patch("builtins.input", return_value=""):
            result = wizard.phase_2_show_instructions()
        assert result["success"] is True
        assert "mandates.md" in result["copied_files"]


class TestGetEnforcementLabel:
    def test_returns_default_when_no_config(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        result = wizard._get_enforcement_label()
        assert result == "Alertas"

    def test_returns_label_from_config(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text(
            json.dumps({"enforcement_mode": "strict_mode"}), encoding="utf-8"
        )
        result = wizard._get_enforcement_label()
        assert result == "Bloquear"

    def test_returns_default_on_invalid_json(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text("not-json{{", encoding="utf-8")
        result = wizard._get_enforcement_label()
        assert result == "Alertas"

    def test_returns_silent_label(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text(
            json.dumps({"enforcement_mode": "silent_mode"}), encoding="utf-8"
        )
        result = wizard._get_enforcement_label()
        assert result == "Sem Alertas"


class TestRunMethod:
    def test_returns_false_on_keyboard_interrupt(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with patch.object(wizard, "show_phase_menu", side_effect=KeyboardInterrupt):
            result = wizard.run()
        assert result is False

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with patch.object(wizard, "show_phase_menu", side_effect=RuntimeError("boom")):
            result = wizard.run()
        assert result is False

    def test_dispatches_to_phase_1(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with (
            patch.object(wizard, "show_phase_menu", return_value="1"),
            patch.object(
                wizard,
                "phase_1_generate_templates",
                return_value={"success": True},
            ) as mock_p1,
        ):
            result = wizard.run()
        assert result is True
        mock_p1.assert_called_once()

    def test_dispatches_to_phase_2(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with (
            patch.object(wizard, "show_phase_menu", return_value="2"),
            patch.object(
                wizard,
                "phase_2_show_instructions",
                return_value={"success": True},
            ) as mock_p2,
        ):
            wizard.run()
        mock_p2.assert_called_once()

    def test_dispatches_to_phase_3(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with (
            patch.object(wizard, "show_phase_menu", return_value="3"),
            patch.object(
                wizard,
                "phase_3_compile_templates",
                return_value={"success": True},
            ) as mock_p3,
        ):
            wizard.run()
        mock_p3.assert_called_once()

    def test_dispatches_to_phase_4(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with (
            patch.object(wizard, "show_phase_menu", return_value="4"),
            patch.object(
                wizard,
                "phase_4_generate_project",
                return_value={"success": True},
            ) as mock_p1,
        ):
            wizard.run()
        mock_p1.assert_called_once()

    def test_returns_false_for_invalid_choice(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with patch.object(wizard, "show_phase_menu", return_value="9"):
            result = wizard.run()
        assert result is False


class TestRunInteractiveWizard:
    def test_creates_wizard_and_runs(self, tmp_path: Path) -> None:
        from sdd_wizard.src.interactive_mode import run_interactive_wizard

        mock_paths = {
            "root": tmp_path,
            "client_build": tmp_path / "generated" / "client" / "build",
            "client_compiled": tmp_path / "generated" / "client" / "compiled",
            "master_compiled": tmp_path / "generated" / "master" / "compiled",
            "client_context": tmp_path / "generated" / "client" / "context",
        }
        with (
            patch(
                "sdd_wizard.src.interactive_mode.get_sdd_paths", return_value=mock_paths
            ),
            patch(
                "sdd_wizard.src.interactive_mode.InteractiveWizard.run",
                return_value=True,
            ),
        ):
            result = run_interactive_wizard(tmp_path)
        assert result is True


class TestAskUserPreferences:
    def test_returns_config_dict(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with patch("builtins.input", side_effect=["2", "1"]):
            config = wizard.ask_user_preferences()
        assert config["language"] == "Python"
        assert config["enforcement_mode"] == "warn_mode"

    def test_defaults_for_invalid_choices(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with patch("builtins.input", side_effect=["99", "99"]):
            config = wizard.ask_user_preferences()
        assert config["language"] == "Python"
        assert config["enforcement_mode"] == "silent_mode"

    def test_strict_mode_choice(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with patch("builtins.input", side_effect=["3", "2"]):
            config = wizard.ask_user_preferences()
        assert config["enforcement_mode"] == "strict_mode"
        assert config["language"] == "Java"


class TestPhase1GenerateTemplates:
    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        mock_generator = MagicMock()
        mock_generator.run.return_value = {"success": True}
        with (
            patch("builtins.input", side_effect=["1", "1"]),
            patch.object(wizard, "_ensure_docs_meta_ready", return_value=(True, "")),
            patch(
                "sdd_wizard.orchestration.wizard.phase1_generator.Phase1Generator",
                return_value=mock_generator,
            ),
        ):
            result = wizard.phase_1_generate_templates()
        assert result["success"] is True

    def test_returns_false_when_generator_fails(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        mock_generator = MagicMock()
        mock_generator.run.return_value = {"success": False}
        with (
            patch("builtins.input", side_effect=["1", "1"]),
            patch.object(wizard, "_ensure_docs_meta_ready", return_value=(True, "")),
            patch(
                "sdd_wizard.orchestration.wizard.phase1_generator.Phase1Generator",
                return_value=mock_generator,
            ),
        ):
            result = wizard.phase_1_generate_templates()
        assert result["success"] is False

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with (
            patch("builtins.input", side_effect=["1", "1"]),
            patch.object(wizard, "_ensure_docs_meta_ready", return_value=(True, "")),
            patch(
                "sdd_wizard.orchestration.wizard.phase1_generator.Phase1Generator",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = wizard.phase_1_generate_templates()
        assert result["success"] is False

    def test_detailed_result_includes_config_and_language(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        mock_generator = MagicMock()
        mock_generator.run.return_value = {"success": True}
        with (
            patch("builtins.input", side_effect=["2", "1"]),
            patch.object(wizard, "_ensure_docs_meta_ready", return_value=(True, "")),
            patch(
                "sdd_wizard.orchestration.wizard.phase1_generator.Phase1Generator",
                return_value=mock_generator,
            ),
        ):
            result = wizard.phase_1_generate_templates()
        assert result["success"] is True
        assert result["language"] == "Python"
        assert result["enforcement_mode"] == "warn_mode"
        assert result["config_path"].endswith("wizard-config.json")

    def test_returns_false_when_docs_meta_bootstrap_fails(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with (
            patch("builtins.input", side_effect=["1", "1"]),
            patch.object(
                wizard,
                "_ensure_docs_meta_ready",
                return_value=(False, "bootstrap failed"),
            ),
        ):
            result = wizard.phase_1_generate_templates()
        assert result["success"] is False
        assert result["error"] == "bootstrap failed"


class TestPhase3CompileTemplates:
    def test_returns_false_when_phase2_input_missing(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        result = wizard.phase_3_compile_templates()
        assert result["success"] is False

    def test_returns_true_on_successful_compile(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.phase2_input_dir.mkdir(parents=True, exist_ok=True)
        mock_compiler = MagicMock()
        mock_compiler.run.return_value = {
            "success": True,
            "mandates": 3,
            "guidelines": 2,
            "files": ["governance-core.json"],
            "output_path": str(tmp_path),
        }
        with (
            patch(
                "sdd_wizard.orchestration.wizard.phase3_compiler.Phase3Compiler",
                return_value=mock_compiler,
            ),
            patch.object(wizard, "phase_6_generate_seedlings", return_value=True),
        ):
            result = wizard.phase_3_compile_templates()
        assert result["success"] is True

    def test_returns_true_even_when_phase6_fails(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.phase2_input_dir.mkdir(parents=True, exist_ok=True)
        mock_compiler = MagicMock()
        mock_compiler.run.return_value = {
            "success": True,
            "mandates": 1,
            "guidelines": 0,
            "files": [],
            "output_path": str(tmp_path),
        }
        with (
            patch(
                "sdd_wizard.orchestration.wizard.phase3_compiler.Phase3Compiler",
                return_value=mock_compiler,
            ),
            patch.object(wizard, "phase_6_generate_seedlings", return_value=False),
        ):
            result = wizard.phase_3_compile_templates()
        assert result["success"] is True

    def test_returns_false_when_compile_fails(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.phase2_input_dir.mkdir(parents=True, exist_ok=True)
        mock_compiler = MagicMock()
        mock_compiler.run.return_value = {"success": False, "error": "failed"}
        with patch(
            "sdd_wizard.orchestration.wizard.phase3_compiler.Phase3Compiler",
            return_value=mock_compiler,
        ):
            result = wizard.phase_3_compile_templates()
        assert result["success"] is False

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.phase2_input_dir.mkdir(parents=True, exist_ok=True)
        with patch(
            "sdd_wizard.orchestration.wizard.phase3_compiler.Phase3Compiler",
            side_effect=RuntimeError("crash"),
        ):
            result = wizard.phase_3_compile_templates()
        assert result["success"] is False

    def test_detailed_result_reports_seedlings_failure(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.phase2_input_dir.mkdir(parents=True, exist_ok=True)
        mock_compiler = MagicMock()
        mock_compiler.run.return_value = {
            "success": True,
            "mandates": 2,
            "guidelines": 1,
            "files": ["governance-core.json"],
            "output_path": str(tmp_path),
        }
        with (
            patch(
                "sdd_wizard.orchestration.wizard.phase3_compiler.Phase3Compiler",
                return_value=mock_compiler,
            ),
            patch.object(wizard, "phase_6_generate_seedlings", return_value=False),
        ):
            result = wizard.phase_3_compile_templates()
        assert result["success"] is True
        assert result["seedlings_success"] is False
        assert result["mandates"] == 2


class TestPhase4GenerateProject:
    def test_returns_false_when_config_missing(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        result = wizard.phase_4_generate_project()
        assert result["success"] is False

    def test_returns_false_when_phase3_output_missing(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text('{"language": "Python"}', encoding="utf-8")
        result = wizard.phase_4_generate_project()
        assert result["success"] is False

    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text('{"language": "Python"}', encoding="utf-8")
        wizard.client_compiled_dir.mkdir(parents=True, exist_ok=True)

        mock_result = {
            "success": True,
            "mandates": 3,
            "guidelines": 2,
            "categories": ["git", "testing"],
        }
        with (
            patch("builtins.input", return_value=""),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.run_phase_4_5_6_generator",
                return_value=mock_result,
            ),
            patch.object(
                wizard,
                "_consolidate_final_template",
                return_value={"success": True, "moved_items": 1},
            ),
        ):
            result = wizard.phase_4_generate_project()
        assert result["success"] is True

    def test_returns_false_when_consolidate_fails(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text('{"language": "Python"}', encoding="utf-8")
        wizard.client_compiled_dir.mkdir(parents=True, exist_ok=True)

        mock_result = {
            "success": True,
            "mandates": 1,
            "guidelines": 0,
            "categories": [],
        }
        with (
            patch("builtins.input", return_value=""),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.run_phase_4_5_6_generator",
                return_value=mock_result,
            ),
            patch.object(
                wizard,
                "_consolidate_final_template",
                return_value={"success": False, "moved_items": 0},
            ),
        ):
            result = wizard.phase_4_generate_project()
        assert result["success"] is False

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text('{"language": "Python"}', encoding="utf-8")
        wizard.client_compiled_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch("builtins.input", return_value=""),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.run_phase_4_5_6_generator",
                side_effect=RuntimeError("crash"),
            ),
        ):
            result = wizard.phase_4_generate_project()
        assert result["success"] is False

    def test_detailed_result_reports_consolidation_failure(
        self, tmp_path: Path
    ) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text('{"language": "Python"}', encoding="utf-8")
        wizard.client_compiled_dir.mkdir(parents=True, exist_ok=True)

        mock_result = {
            "success": True,
            "mandates": 3,
            "guidelines": 2,
            "categories": ["git"],
        }
        with (
            patch("builtins.input", return_value=""),
            patch(
                "sdd_wizard.orchestration.phase_4_5_6_generator.run_phase_4_5_6_generator",
                return_value=mock_result,
            ),
            patch.object(
                wizard,
                "_consolidate_final_template",
                return_value={"success": False, "moved_items": 0},
            ),
        ):
            result = wizard.phase_4_generate_project()

        assert result["success"] is False
        assert result["consolidated"] is False
        assert result["mandates"] == 3


class TestPhase6GenerateSeedlings:
    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        wizard.client_build_dir.mkdir(parents=True, exist_ok=True)
        wizard.wizard_config_path.write_text(
            '{"language": "Python", "enforcement_mode": "warn_mode"}',
            encoding="utf-8",
        )

        mock_loader = MagicMock()
        mock_loader.load.return_value = True
        mock_loader.mandates = []
        mock_loader.guidelines_by_category = {}

        mock_orchestrator = MagicMock()
        mock_orchestrator.generate.return_value = True

        mock_paths = {
            "client_compiled": tmp_path / "generated" / "client" / "compiled",
        }
        with (
            patch("sdd_core.utils.environment.get_sdd_paths", return_value=mock_paths),
            patch(
                "sdd_wizard.orchestration.phase4_governance_loader.GovernanceLoader",
                return_value=mock_loader,
            ),
            patch(
                "sdd_wizard.orchestration.phase6_seedlings_orchestrator.SeedlingsOrchestrator",
                return_value=mock_orchestrator,
            ),
        ):
            result = wizard.phase_6_generate_seedlings(tmp_path)
        assert result is True

    def test_returns_false_when_loader_fails(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        mock_loader = MagicMock()
        mock_loader.load.return_value = False

        mock_paths = {"client_compiled": tmp_path / "generated" / "client" / "compiled"}
        with (
            patch("sdd_core.utils.environment.get_sdd_paths", return_value=mock_paths),
            patch(
                "sdd_wizard.orchestration.phase4_governance_loader.GovernanceLoader",
                return_value=mock_loader,
            ),
        ):
            result = wizard.phase_6_generate_seedlings(tmp_path)
        assert result is False

    def test_returns_false_on_exception(self, tmp_path: Path) -> None:
        wizard = _make_wizard(tmp_path)
        with patch(
            "sdd_core.utils.environment.get_sdd_paths",
            side_effect=RuntimeError("no paths"),
        ):
            result = wizard.phase_6_generate_seedlings(tmp_path)
        assert result is False
