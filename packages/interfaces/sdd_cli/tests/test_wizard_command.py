"""Tests for `sdd wizard run` command behavior."""

from __future__ import annotations

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
