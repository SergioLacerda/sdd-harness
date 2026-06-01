"""Tests for sdd_cli.commands.docs — deploy command coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd_cli.main import app

runner = CliRunner()
pytestmark = pytest.mark.unit


class TestDocsDeploy:
    def test_no_mkdocs_config_skips(self) -> None:
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 0
        assert "Skipping docs deploy" in result.output

    def test_mkdocs_yaml_also_accepted(self) -> None:
        with runner.isolated_filesystem():
            Path("mkdocs.yaml").write_text("", encoding="utf-8")
            with patch("shutil.which", return_value=None):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 1
        assert "mkdocs command not found" in result.output

    def test_mkdocs_not_in_path_exits_1(self) -> None:
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with patch("shutil.which", return_value=None):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 1
        assert "mkdocs command not found" in result.output

    def test_deploy_success_with_force(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy", "--force"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert "--force" in called_cmd

    def test_deploy_success_without_force(self) -> None:
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy", "--no-force"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert "--force" not in called_cmd

    def test_non_zero_exit_error_exits_1(self) -> None:
        from sdd_core.utils.process import ProcessNonZeroExitError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessNonZeroExitError("mkdocs failed")
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 1
        assert "docs deploy failed" in result.output

    def test_authorization_error_exits_2(self) -> None:
        from sdd_core.utils.process import ProcessAuthorizationError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessAuthorizationError("blocked")
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 2
        assert "blocked by policy" in result.output

    def test_timeout_error_exits_124(self) -> None:
        from sdd_core.utils.process import ProcessTimeoutError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessTimeoutError(["mkdocs", "gh-deploy"], 30.0)
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 124
        assert "timed out" in result.output

    def test_spawn_error_exits_127(self) -> None:
        from sdd_core.utils.process import ProcessSpawnError

        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessSpawnError("cannot spawn")
        with runner.isolated_filesystem():
            Path("mkdocs.yml").write_text("", encoding="utf-8")
            with (
                patch("shutil.which", return_value="/usr/bin/mkdocs"),
                patch(
                    "sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner
                ),
            ):
                result = runner.invoke(app, ["docs", "deploy"])
        assert result.exit_code == 127
        assert "could not start" in result.output
