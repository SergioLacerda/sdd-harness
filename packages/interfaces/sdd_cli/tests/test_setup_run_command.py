"""Tests for sdd_cli.commands.setup — `sdd setup run` orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd_cli.commands import setup as setup_mod

runner = CliRunner()
pytestmark = pytest.mark.unit


class TestRunSetup:
    def _make_venv(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        bin_dir = venv / "bin"
        bin_dir.mkdir()
        (bin_dir / "python").write_text("#!/bin/sh\n", encoding="utf-8")
        (bin_dir / "python").chmod(0o755)
        (bin_dir / "sdd").write_text("#!/bin/sh\n", encoding="utf-8")
        (bin_dir / "sdd").chmod(0o755)

    def test_run_setup_happy_path(self, tmp_path: Path) -> None:
        from sdd_cli.main import app

        self._make_venv(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)

        with (
            patch.object(setup_mod, "_REPO_ROOT", tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch.object(setup_mod, "_validate_module_import", return_value=True),
            patch(
                "sdd_cli.commands.setup.resolve_venv_python",
                return_value="/venv/bin/python",
            ),
            patch(
                "sdd_cli.commands.setup.resolve_venv_sdd",
                return_value="/venv/bin/sdd",
            ),
        ):
            result = runner.invoke(app, ["setup", "run", "--no-hooks"])

        assert result.exit_code == 0
        assert "completed" in result.output.lower()

    def test_run_setup_venv_python_not_found_exits_1(self, tmp_path: Path) -> None:
        from sdd_cli.main import app

        self._make_venv(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)

        with (
            patch.object(setup_mod, "_REPO_ROOT", tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch(
                "sdd_cli.commands.setup.resolve_venv_python",
                side_effect=RuntimeError("not found"),
            ),
        ):
            result = runner.invoke(app, ["setup", "run", "--no-hooks"])

        assert result.exit_code == 1
        assert "venv python" in result.output.lower()

    def test_run_setup_module_import_fails_exits_1(self, tmp_path: Path) -> None:
        from sdd_cli.main import app

        self._make_venv(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)

        with (
            patch.object(setup_mod, "_REPO_ROOT", tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch.object(setup_mod, "_validate_module_import", return_value=False),
            patch(
                "sdd_cli.commands.setup.resolve_venv_python",
                return_value="/venv/bin/python",
            ),
        ):
            result = runner.invoke(app, ["setup", "run", "--no-hooks"])

        assert result.exit_code == 1
        assert "FAILED" in result.output

    def test_run_setup_sdd_cli_not_found_exits_1(self, tmp_path: Path) -> None:
        from sdd_cli.main import app

        self._make_venv(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)

        with (
            patch.object(setup_mod, "_REPO_ROOT", tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch.object(setup_mod, "_validate_module_import", return_value=True),
            patch(
                "sdd_cli.commands.setup.resolve_venv_python",
                return_value="/venv/bin/python",
            ),
            patch(
                "sdd_cli.commands.setup.resolve_venv_sdd",
                side_effect=RuntimeError("not found"),
            ),
        ):
            result = runner.invoke(app, ["setup", "run", "--no-hooks"])

        assert result.exit_code == 1
        assert "sdd CLI not found" in result.output

    def test_run_setup_cli_not_responding_exits_1(self, tmp_path: Path) -> None:
        from sdd_cli.main import app

        self._make_venv(tmp_path)
        mock_runner = MagicMock()
        # First calls succeed (pip, installs), last call (sdd --help) fails
        mock_runner.run.return_value = MagicMock(success=False)

        with (
            patch.object(setup_mod, "_REPO_ROOT", tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch.object(setup_mod, "_validate_module_import", return_value=True),
            patch(
                "sdd_cli.commands.setup.resolve_venv_python",
                return_value="/venv/bin/python",
            ),
            patch(
                "sdd_cli.commands.setup.resolve_venv_sdd",
                return_value="/venv/bin/sdd",
            ),
        ):
            result = runner.invoke(app, ["setup", "run", "--no-hooks"])

        # Either fails due to package install or CLI check
        assert result.exit_code != 0

    def test_run_setup_bootstraps_pip_when_missing(self, tmp_path: Path) -> None:
        from sdd_cli.main import app

        self._make_venv(tmp_path)
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)

        # First _validate_module_import call (pip check) returns False,
        # remaining calls (sdd_core, sdd_wizard, sdd_cli) return True.
        with (
            patch.object(setup_mod, "_REPO_ROOT", tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
            patch.object(
                setup_mod,
                "_validate_module_import",
                side_effect=[False, True, True, True],
            ),
            patch(
                "sdd_cli.commands.setup.resolve_venv_python",
                return_value="/venv/bin/python",
            ),
            patch(
                "sdd_cli.commands.setup.resolve_venv_sdd",
                return_value="/venv/bin/sdd",
            ),
        ):
            result = runner.invoke(app, ["setup", "run", "--no-hooks"])

        assert result.exit_code == 0
        calls_str = str(mock_runner.run.call_args_list)
        assert "ensurepip" in calls_str
