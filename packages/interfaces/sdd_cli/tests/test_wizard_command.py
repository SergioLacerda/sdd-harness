"""Tests for `sdd wizard run` command behavior."""

from __future__ import annotations

import builtins
import sys
from unittest.mock import patch

from typer.testing import CliRunner

from sdd_cli.commands.wizard import app


def test_wizard_run_reports_actionable_error_when_project_root_not_found() -> None:
    runner = CliRunner()
    with patch(
        "sdd_wizard.contracts.run_wizard",
        side_effect=RuntimeError(
            "SDD Project root not found. Ensure you are running from within the repository."
        ),
    ):
        result = runner.invoke(app, ["run"])

    assert result.exit_code == 1
    assert "No SDD project context found" in result.output
    assert "sdd wizard run" in result.output


def test_wizard_run_reraises_unrelated_runtime_error() -> None:
    runner = CliRunner()
    with patch(
        "sdd_wizard.contracts.run_wizard",
        side_effect=RuntimeError("unrelated failure"),
    ):
        result = runner.invoke(app, ["run"])

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert "unrelated failure" in str(result.exception)


def test_wizard_run_exits_when_result_is_unsuccessful() -> None:
    from sdd_wizard.contracts import WizardResult

    runner = CliRunner()
    with patch(
        "sdd_wizard.contracts.run_wizard",
        return_value=WizardResult(success=False, errors=["boom"]),
    ):
        result = runner.invoke(app, ["run"])

    assert result.exit_code == 1


def test_wizard_run_passes_through_from_file_and_non_interactive(
    tmp_path,
) -> None:
    from sdd_wizard.contracts import WizardInvocation

    custom_file = tmp_path / "custom-governance.json"
    custom_file.write_text("{}", encoding="utf-8")
    runner = CliRunner()
    recorded: list[WizardInvocation] = []

    def _fake_run_wizard(invocation: WizardInvocation):
        from sdd_wizard.contracts import WizardResult

        recorded.append(invocation)
        return WizardResult(success=True)

    with patch("sdd_wizard.contracts.run_wizard", side_effect=_fake_run_wizard):
        result = runner.invoke(
            app,
            ["run", "--from-file", str(custom_file), "--non-interactive"],
        )

    assert result.exit_code == 0, result.output
    assert recorded[0].custom_governance_path == custom_file.resolve()
    assert recorded[0].non_interactive is True


def test_wizard_run_reports_error_when_sdd_wizard_not_installed() -> None:
    runner = CliRunner()
    real_import = builtins.__import__

    def _fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "sdd_wizard.contracts":
            raise ImportError("No module named 'sdd_wizard'")
        return real_import(name, *args, **kwargs)

    with (
        patch.dict(sys.modules, {"sdd_wizard.contracts": None}),
        patch("builtins.__import__", side_effect=_fake_import),
    ):
        result = runner.invoke(app, ["run"])

    assert result.exit_code == 1
    assert "ERROR: sdd-wizard not installed" in result.output
    assert "sdd setup run" in result.output
