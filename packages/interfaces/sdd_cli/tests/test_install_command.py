"""Tests for `sdd install --wizard` command behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from sdd_cli.commands.install import app


def test_install_without_wizard_flag_reports_error() -> None:
    runner = CliRunner()

    result = runner.invoke(app, [])

    assert result.exit_code == 1
    assert "no install target specified" in result.output
    assert "sdd install --wizard" in result.output


def test_install_from_file_without_wizard_flag_reports_specific_error(
    tmp_path: Path,
) -> None:
    custom_file = tmp_path / "custom-governance.json"
    custom_file.write_text("{}", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["--from-file", str(custom_file)])

    assert result.exit_code == 1
    assert "--from-file/--non-interactive require --wizard" in result.output


def test_install_non_interactive_without_wizard_flag_reports_specific_error() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--non-interactive"])

    assert result.exit_code == 1
    assert "--from-file/--non-interactive require --wizard" in result.output


def test_install_wizard_delegates_to_run_wizard_command() -> None:
    runner = CliRunner()
    with patch("sdd_cli.commands.install.run_wizard_command") as mock_run:
        result = runner.invoke(app, ["--wizard"])

    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        output_dir=None, from_file=None, non_interactive=False
    )


def test_install_wizard_passes_through_output_dir(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("sdd_cli.commands.install.run_wizard_command") as mock_run:
        result = runner.invoke(app, ["--wizard", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["output_dir"] == tmp_path


def test_install_wizard_reports_actionable_error_when_project_root_not_found() -> None:
    runner = CliRunner()
    with patch(
        "sdd_wizard.contracts.run_wizard",
        side_effect=RuntimeError(
            "SDD Project root not found. Ensure you are running from within the repository."
        ),
    ):
        result = runner.invoke(app, ["--wizard"])

    assert result.exit_code == 1
    assert "No SDD project context found" in result.output


def test_install_without_direct_root_does_not_deploy(tmp_path: Path) -> None:
    runner = CliRunner()
    with (
        patch("sdd_cli.commands.install.run_wizard_command"),
        patch("sdd_cli.commands.install.deploy_to_root") as mock_deploy,
    ):
        result = runner.invoke(app, ["--wizard"])

    assert result.exit_code == 0
    mock_deploy.assert_not_called()


def test_install_direct_root_deploys_from_resolved_output_dir(tmp_path: Path) -> None:
    from sdd_wizard.orchestration.wizard._direct_root_deploy import DeployToRootResult

    runner = CliRunner()
    with (
        patch("sdd_cli.commands.install.run_wizard_command"),
        patch(
            "sdd_cli.commands.install.deploy_to_root",
            return_value=DeployToRootResult(created=["AGENTS.md"]),
        ) as mock_deploy,
    ):
        result = runner.invoke(
            app, ["--wizard", "--output-dir", str(tmp_path), "--direct-root"]
        )

    assert result.exit_code == 0, result.output
    mock_deploy.assert_called_once()
    _, kwargs = mock_deploy.call_args
    assert kwargs["final_template_dir"] == tmp_path.resolve()
    assert "created=1" in result.output


def test_install_wizard_passes_through_from_file(tmp_path: Path) -> None:
    custom_file = tmp_path / "custom-governance.json"
    custom_file.write_text("{}", encoding="utf-8")
    runner = CliRunner()
    with patch("sdd_cli.commands.install.run_wizard_command") as mock_run:
        result = runner.invoke(app, ["--wizard", "--from-file", str(custom_file)])

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["from_file"] == custom_file


def test_install_wizard_passes_through_non_interactive() -> None:
    runner = CliRunner()
    with patch("sdd_cli.commands.install.run_wizard_command") as mock_run:
        result = runner.invoke(app, ["--wizard", "--non-interactive"])

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["non_interactive"] is True


def test_install_direct_root_reports_skipped_unmanaged_files() -> None:
    from sdd_wizard.orchestration.wizard._direct_root_deploy import DeployToRootResult

    runner = CliRunner()
    with (
        patch("sdd_cli.commands.install.run_wizard_command"),
        patch(
            "sdd_cli.commands.install.deploy_to_root",
            return_value=DeployToRootResult(skipped=["AGENTS.md"]),
        ),
    ):
        result = runner.invoke(app, ["--wizard", "--direct-root"])

    assert result.exit_code == 0, result.output
    assert "Skipped (unmanaged, not overwritten): AGENTS.md" in result.output
