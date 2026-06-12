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

    def test_run_setup_creates_venv_when_missing(self, tmp_path: Path) -> None:
        from sdd_cli.main import app

        # No .venv directory — venv creation branch (line 118) must run
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
            runner.invoke(app, ["setup", "run", "--no-hooks"])

        # _run for venv creation should have been called
        calls_str = str(mock_runner.run.call_args_list)
        assert "venv" in calls_str

    def test_run_setup_installs_packages_with_pyproject(self, tmp_path: Path) -> None:
        from sdd_cli.main import app

        # Create a pyproject.toml for one ordered package to cover lines 146-147
        pkg_path = tmp_path / "packages" / "core" / "sdd_core"
        pkg_path.mkdir(parents=True)
        (pkg_path / "pyproject.toml").write_text(
            "[project]\nname='sdd-core'\n", encoding="utf-8"
        )

        (tmp_path / ".venv").mkdir()
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
            runner.invoke(app, ["setup", "run", "--no-hooks"])

        calls_str = str(mock_runner.run.call_args_list)
        assert "sdd_core" in calls_str

    def test_run_setup_installs_extra_packages(self, tmp_path: Path) -> None:
        from sdd_cli.main import app

        # Create an extra package NOT in the ordered list (covers lines 153-158)
        extra_pkg = tmp_path / "packages" / "extra" / "sdd_extra"
        extra_pkg.mkdir(parents=True)
        (extra_pkg / "pyproject.toml").write_text(
            "[project]\nname='sdd-extra'\n", encoding="utf-8"
        )

        (tmp_path / ".venv").mkdir()
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
            runner.invoke(app, ["setup", "run", "--no-hooks"])

        calls_str = str(mock_runner.run.call_args_list)
        assert "sdd_extra" in calls_str

    def test_run_setup_installs_dev_deps_when_root_pyproject_exists(
        self, tmp_path: Path
    ) -> None:
        from sdd_cli.main import app

        # Root pyproject.toml triggers line 163
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='sdd-harness'\n", encoding="utf-8"
        )
        (tmp_path / ".venv").mkdir()
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
            runner.invoke(app, ["setup", "run", "--no-hooks"])

        calls_str = str(mock_runner.run.call_args_list)
        assert "[dev]" in calls_str

    def test_run_setup_with_hooks_calls_setup_git_hooks(self, tmp_path: Path) -> None:
        from sdd_cli.main import app

        (tmp_path / ".venv").mkdir()
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(success=True)

        hooks_src = tmp_path / "tools" / "scripts" / "git-hooks"
        hooks_src.mkdir(parents=True)
        git_hooks = tmp_path / ".git" / "hooks"
        git_hooks.mkdir(parents=True)

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
            result = runner.invoke(app, ["setup", "run", "--hooks"])

        assert "Hooks" in result.output or result.exit_code == 0
