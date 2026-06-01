"""Unit tests for `sdd init` command logic.

Tests call the init() Typer callback directly to bypass Typer's type registry,
which does not support Literal[...] annotations in CliRunner.invoke().
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from sdd_cli.commands.init import init

pytestmark = pytest.mark.unit


class TestInitCommand:
    """sdd init creates .sdd/profile and handles edge cases."""

    def test_creates_profile_in_clean_directory(self, tmp_path: Path) -> None:
        with (
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
        ):
            init(type="client", name="test-ws", force=False, no_bootstrap=True)
        profile_path = tmp_path / ".sdd" / "profile"
        assert profile_path.exists()
        content = profile_path.read_text(encoding="utf-8")
        assert "client" in content

    def test_exits_1_if_already_initialized_without_force(self, tmp_path: Path) -> None:
        # Create profile first
        with (
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
        ):
            init(type="client", name="first", force=False, no_bootstrap=True)
        # Second init without --force must exit 1
        with (
            pytest.raises(typer.Exit) as exc_info,
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
        ):
            init(type="client", name="second", force=False, no_bootstrap=True)
        assert exc_info.value.exit_code == 1

    def test_force_overwrites_existing_profile(self, tmp_path: Path) -> None:
        with (
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
        ):
            init(type="client", name="first", force=False, no_bootstrap=True)
            init(type="master", name="second", force=True, no_bootstrap=True)
        content = (tmp_path / ".sdd" / "profile").read_text(encoding="utf-8")
        assert "master" in content

    def test_default_name_equals_type(self, tmp_path: Path) -> None:
        with (
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch("sdd_cli.commands.init.find_workspace_root", return_value=None),
        ):
            init(type="client", name=None, force=False, no_bootstrap=True)
        content = (tmp_path / ".sdd" / "profile").read_text(encoding="utf-8")
        assert "client" in content

    def test_blocks_nested_workspace(self, tmp_path: Path) -> None:
        """init inside an already-initialized workspace parent must fail."""
        parent_sdd = tmp_path / ".sdd"
        with (
            pytest.raises(typer.Exit) as exc_info,
            patch("sdd_cli.commands.init.Path.cwd", return_value=tmp_path),
            patch(
                "sdd_cli.commands.init.find_workspace_root",
                return_value=parent_sdd.parent,
            ),
        ):
            # Simulate parent workspace detected
            init(type="client", name=None, force=False)
        assert exc_info.value.exit_code == 1
