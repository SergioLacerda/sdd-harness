"""Tests for sdd_cli.commands.tools — list and run command coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sdd_cli.commands.tools import _find_repo_root
from sdd_cli.main import app

runner = CliRunner()
pytestmark = pytest.mark.unit


def test_find_repo_root_delegates_to_detect(tmp_path: Path) -> None:
    with patch("sdd_cli.utils.environment.detect_repo_root", return_value=tmp_path):
        assert _find_repo_root() == tmp_path


def _make_tools_dir(root: Path) -> Path:
    tools_dir = root / "tools"
    tools_dir.mkdir()
    return tools_dir


class TestToolsList:
    def test_tools_dir_not_found_exits_1(self, tmp_path: Path) -> None:
        with patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 1
        assert "tools directory not found" in result.output

    def test_lists_python_scripts(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "health_check.py").write_text("", encoding="utf-8")
        with patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0
        assert "health_check.py" in result.output

    def test_skips_dunder_files(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "__init__.py").write_text("", encoding="utf-8")
        (tools_dir / "real_tool.py").write_text("", encoding="utf-8")
        with patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0
        assert "__init__.py" not in result.output
        assert "real_tool.py" in result.output

    def test_lists_nested_scripts(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        sub = tools_dir / "health"
        sub.mkdir()
        (sub / "check.py").write_text("", encoding="utf-8")
        with patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["tools", "list"])
        assert result.exit_code == 0
        assert "check.py" in result.output


class TestToolsRun:
    def test_script_not_found_without_extension_exits_1(self, tmp_path: Path) -> None:
        _make_tools_dir(tmp_path)
        with patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path):
            result = runner.invoke(app, ["tools", "run", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_script_found_with_py_extension_appended(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        script = tools_dir / "check.py"
        script.write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=0)
        with (
            patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
        ):
            result = runner.invoke(app, ["tools", "run", "check"])
        assert result.exit_code == 0

    def test_run_success_with_explicit_py_extension(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        script = tools_dir / "tool.py"
        script.write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=0)
        with (
            patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
        ):
            result = runner.invoke(app, ["tools", "run", "tool.py"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert "uv" in called_cmd

    def test_run_passes_extra_args(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "tool.py").write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=0)
        with (
            patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
        ):
            result = runner.invoke(app, ["tools", "run", "tool.py", "extra_arg"])
        assert result.exit_code == 0
        called_cmd = mock_runner.run.call_args[0][0]
        assert "extra_arg" in called_cmd

    def test_authorization_error_exits_2(self, tmp_path: Path) -> None:
        from sdd_core.utils.process import ProcessAuthorizationError

        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "tool.py").write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessAuthorizationError("blocked")
        with (
            patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
        ):
            result = runner.invoke(app, ["tools", "run", "tool.py"])
        assert result.exit_code == 2
        assert "blocked by policy" in result.output

    def test_spawn_error_exits_127(self, tmp_path: Path) -> None:
        from sdd_core.utils.process import ProcessSpawnError

        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "tool.py").write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.side_effect = ProcessSpawnError("uv not found")
        with (
            patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
        ):
            result = runner.invoke(app, ["tools", "run", "tool.py"])
        assert result.exit_code == 127
        assert "uv" in result.output

    def test_non_zero_returncode_propagates(self, tmp_path: Path) -> None:
        tools_dir = _make_tools_dir(tmp_path)
        (tools_dir / "tool.py").write_text("", encoding="utf-8")
        mock_runner = MagicMock()
        mock_runner.run.return_value = MagicMock(returncode=42)
        with (
            patch("sdd_cli.commands.tools._find_repo_root", return_value=tmp_path),
            patch("sdd_core.utils.process.SafeProcessRunner", return_value=mock_runner),
        ):
            result = runner.invoke(app, ["tools", "run", "tool.py"])
        assert result.exit_code == 42
