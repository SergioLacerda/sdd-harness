"""Tests for `sdd governance hook status|disable|enable`."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sdd_cli.main import app

runner = CliRunner()


def test_hook_disable_creates_sentinel(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        (root / ".sdd").mkdir()

        result = runner.invoke(app, ["governance", "hook", "disable"])

        assert result.exit_code == 0
        assert (root / ".sdd" / "runtime" / "hook-disabled").exists()


def test_hook_enable_removes_sentinel(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        sentinel = root / ".sdd" / "runtime" / "hook-disabled"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("", encoding="utf-8")

        result = runner.invoke(app, ["governance", "hook", "enable"])

        assert result.exit_code == 0
        assert not sentinel.exists()


def test_hook_enable_when_already_absent_does_not_error(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        (root / ".sdd").mkdir()

        result = runner.invoke(app, ["governance", "hook", "enable"])

        assert result.exit_code == 0


def test_hook_status_reports_enabled_when_sentinel_absent(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        (root / ".sdd").mkdir()

        result = runner.invoke(app, ["governance", "hook", "status"])

        assert result.exit_code == 0
        assert "enabled" in result.output.lower()


def test_hook_status_reports_disabled_when_sentinel_present(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        root = Path.cwd()
        sentinel = root / ".sdd" / "runtime" / "hook-disabled"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("", encoding="utf-8")

        result = runner.invoke(app, ["governance", "hook", "status"])

        assert result.exit_code == 0
        assert "disabled" in result.output.lower()
