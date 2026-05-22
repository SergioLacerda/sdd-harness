"""Unit tests for sdd_core.utils.environment."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from tests.helpers.text_io import write_text_utf8

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# WorkspaceNotInitializedError
# ---------------------------------------------------------------------------


class TestWorkspaceNotInitializedError:
    def test_message_contains_start_path(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import WorkspaceNotInitializedError

        err = WorkspaceNotInitializedError(tmp_path)
        assert str(tmp_path) in str(err)

    def test_is_runtime_error(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import WorkspaceNotInitializedError

        err = WorkspaceNotInitializedError(tmp_path)
        assert isinstance(err, RuntimeError)


# ---------------------------------------------------------------------------
# ProfileContext
# ---------------------------------------------------------------------------


class TestProfileContext:
    def _make(self, profile_type: str = "client") -> Any:
        from typing import cast

        from sdd_core.utils.environment import ProfileContext

        return ProfileContext(
            type=cast(Any, profile_type),
            name="test",
            workspace_id="abc",
            core_hash="hash",
            root=Path("/tmp/workspace"),
        )

    def test_is_master_true_for_master(self) -> None:
        ctx = self._make("master")
        assert ctx.is_master is True
        assert ctx.is_client is False

    def test_is_client_true_for_client(self) -> None:
        ctx = self._make("client")
        assert ctx.is_client is True
        assert ctx.is_master is False

    def test_as_dict_contains_expected_keys(self) -> None:
        ctx = self._make("client")
        d = ctx.as_dict()
        assert "profile" in d
        assert "name" in d
        assert "workspace_id" in d
        assert "core_hash" in d
        assert "root" in d
        assert "is_master" in d
        assert "is_client" in d

    def test_frozen_immutable(self) -> None:
        ctx = self._make("client")
        with pytest.raises((AttributeError, TypeError)):
            ctx.name = "changed"


# ---------------------------------------------------------------------------
# is_repo_root
# ---------------------------------------------------------------------------


class TestIsRepoRoot:
    def test_returns_false_for_empty_dir(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import is_repo_root

        assert is_repo_root(tmp_path) is False

    def test_returns_true_when_required_files_present(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import is_repo_root

        (tmp_path / "pyproject.toml").write_text("[tool.sdd]", encoding="utf-8")
        core_dir = tmp_path / "packages" / "core" / "sdd_core"
        core_dir.mkdir(parents=True)
        (core_dir / "pyproject.toml").write_text("[tool.sdd]", encoding="utf-8")

        assert is_repo_root(tmp_path) is True

    def test_partial_structure_returns_false(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import is_repo_root

        # Only top-level pyproject.toml, no packages/core/sdd_core/pyproject.toml
        (tmp_path / "pyproject.toml").write_text("[tool.sdd]", encoding="utf-8")
        assert is_repo_root(tmp_path) is False


# ---------------------------------------------------------------------------
# find_workspace_root
# ---------------------------------------------------------------------------


class TestFindWorkspaceRoot:
    def test_returns_none_when_no_sdd_dir(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import find_workspace_root

        result = find_workspace_root(start=tmp_path)
        assert result is None

    def test_finds_sdd_dir_in_start(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import find_workspace_root

        (tmp_path / ".sdd").mkdir()
        result = find_workspace_root(start=tmp_path)
        assert result == tmp_path

    def test_finds_sdd_dir_in_parent(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import find_workspace_root

        (tmp_path / ".sdd").mkdir()
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        result = find_workspace_root(start=nested)
        assert result == tmp_path


# ---------------------------------------------------------------------------
# resolve_profile
# ---------------------------------------------------------------------------


class TestResolveProfile:
    def test_override_master_returns_master_profile(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_profile

        ctx = resolve_profile(root=tmp_path, override="master")
        assert ctx.type == "master"

    def test_override_client_returns_client_profile(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_profile

        ctx = resolve_profile(root=tmp_path, override="client")
        assert ctx.type == "client"

    def test_env_var_override_takes_effect(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from sdd_core.utils.environment import resolve_profile

        monkeypatch.setenv("SDD_PROFILE", "master")
        ctx = resolve_profile(root=tmp_path)
        assert ctx.type == "master"
        monkeypatch.delenv("SDD_PROFILE")

    def test_raises_when_no_sdd_dir_and_no_override(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import (
            WorkspaceNotInitializedError,
            resolve_profile,
        )

        # No .sdd/profile file exists, no override
        with pytest.raises(WorkspaceNotInitializedError):
            resolve_profile(root=tmp_path)

    def test_reads_valid_profile_file(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_profile

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        profile_path = sdd_dir / "profile"
        write_text_utf8(
            profile_path,
            "[sdd]\ntype = master\nname = my-workspace\nworkspace_id = abc123\ncore_hash = ff00\n",
        )

        ctx = resolve_profile(root=tmp_path)
        assert ctx.type == "master"
        assert ctx.name == "my-workspace"
        assert ctx.workspace_id == "abc123"
        assert ctx.core_hash == "ff00"

    def test_raises_for_invalid_type_in_profile(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import (
            WorkspaceNotInitializedError,
            resolve_profile,
        )

        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        profile_path = sdd_dir / "profile"
        profile_path.write_text("[sdd]\ntype = unknown\n", encoding="utf-8")

        with pytest.raises(WorkspaceNotInitializedError):
            resolve_profile(root=tmp_path)


# ---------------------------------------------------------------------------
# write_profile
# ---------------------------------------------------------------------------


class TestWriteProfile:
    def test_writes_profile_file(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import write_profile

        ctx = write_profile(tmp_path, "client", "test-workspace")
        profile_path = tmp_path / ".sdd" / "profile"
        assert profile_path.exists()
        assert ctx.type == "client"
        assert ctx.name == "test-workspace"
        assert ctx.workspace_id != ""

    def test_creates_sdd_dir(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import write_profile

        write_profile(tmp_path, "master", "master-ws")
        assert (tmp_path / ".sdd").is_dir()

    def test_profile_is_readable_after_write(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_profile, write_profile

        write_profile(tmp_path, "client", "my-client")
        ctx = resolve_profile(root=tmp_path)
        assert ctx.type == "client"
        assert ctx.name == "my-client"


# ---------------------------------------------------------------------------
# detect_profile (backward compat)
# ---------------------------------------------------------------------------


class TestDetectProfile:
    def test_returns_client_when_no_workspace(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import detect_profile

        # No .sdd/profile → should return 'client' as fallback
        result = detect_profile(root=tmp_path)
        assert result == "client"

    def test_returns_master_when_profile_is_master(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import detect_profile, write_profile

        write_profile(tmp_path, "master", "m")
        result = detect_profile(root=tmp_path)
        assert result == "master"


# ---------------------------------------------------------------------------
# resolve_venv_python / resolve_venv_sdd
# ---------------------------------------------------------------------------


class TestResolveVenvPython:
    def test_finds_linux_python(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_venv_python

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        python = bin_dir / "python"
        python.write_text("#!/bin/python", encoding="utf-8")

        result = resolve_venv_python(tmp_path)
        assert result == python

    def test_finds_windows_python(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_venv_python

        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        python_exe = scripts_dir / "python.exe"
        python_exe.write_text("exe", encoding="utf-8")

        result = resolve_venv_python(tmp_path)
        assert result == python_exe

    def test_raises_when_not_found(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_venv_python

        with pytest.raises(RuntimeError, match="Could not find virtualenv python"):
            resolve_venv_python(tmp_path)


class TestResolveVenvSdd:
    def test_finds_linux_sdd(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_venv_sdd

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        sdd = bin_dir / "sdd"
        sdd.write_text("#!/bin/sdd", encoding="utf-8")

        result = resolve_venv_sdd(tmp_path)
        assert result == sdd

    def test_finds_windows_sdd(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_venv_sdd

        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        sdd_exe = scripts_dir / "sdd.exe"
        sdd_exe.write_text("exe", encoding="utf-8")

        result = resolve_venv_sdd(tmp_path)
        assert result == sdd_exe

    def test_raises_when_not_found(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_venv_sdd

        with pytest.raises(RuntimeError, match="Could not find sdd executable"):
            resolve_venv_sdd(tmp_path)


# ---------------------------------------------------------------------------
# get_profile_context (deprecated helper)
# ---------------------------------------------------------------------------


class TestGetProfileContext:
    def test_returns_dict_with_required_keys(self) -> None:
        from sdd_core.utils.environment import get_profile_context

        result = get_profile_context("client")
        assert "profile" in result
        assert "root" in result
        assert "paths" in result
        assert "is_master" in result
        assert "is_client" in result

    def test_client_profile_flags(self) -> None:
        from sdd_core.utils.environment import get_profile_context

        result = get_profile_context("client")
        assert result["is_client"] is True
        assert result["is_master"] is False

    def test_master_profile_flags(self) -> None:
        from sdd_core.utils.environment import get_profile_context

        result = get_profile_context("master")
        assert result["is_master"] is True
        assert result["is_client"] is False


class TestDetectRepoRootFallbacks:
    def test_uses_github_workspace_env(self, monkeypatch: Any, tmp_path: Path) -> None:
        from sdd_core.utils.environment import detect_repo_root

        # Make is_repo_root return False for all paths to force fallback
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
        with patch("sdd_core.utils.environment.is_repo_root", return_value=False):
            result = detect_repo_root()
        assert result == tmp_path.resolve()

    def test_raises_when_not_found(self, monkeypatch: Any) -> None:
        from sdd_core.utils.environment import detect_repo_root

        monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
        with (
            patch("sdd_core.utils.environment.is_repo_root", return_value=False),
            pytest.raises(RuntimeError),
        ):
            detect_repo_root()


class TestGetProjectConfig:
    def test_returns_empty_when_toml_read_fails(self, tmp_path: Path) -> None:
        from sdd_core.utils.environment import get_project_config

        # Point to a path where pyproject.toml exists but has bad content
        (tmp_path / "pyproject.toml").write_bytes(b"\xff\xfe bad toml")
        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            result = get_project_config()
        assert result == {}

    def test_returns_dict_on_success(self) -> None:
        from sdd_core.utils.environment import get_project_config

        result = get_project_config()
        # Should return a dict (may be empty if toml not available)
        assert isinstance(result, dict)


class TestResolveProfileWithOverride:
    def test_env_var_override_master(self, monkeypatch: Any, tmp_path: Path) -> None:
        from sdd_core.utils.environment import resolve_profile

        monkeypatch.setenv("SDD_PROFILE", "master")
        ctx = resolve_profile(root=tmp_path)
        assert ctx.type == "master"
        monkeypatch.delenv("SDD_PROFILE")

    def test_raises_when_no_workspace_and_no_override(
        self, monkeypatch: Any, tmp_path: Path
    ) -> None:
        from sdd_core.utils.environment import (
            WorkspaceNotInitializedError,
            resolve_profile,
        )

        monkeypatch.delenv("SDD_PROFILE", raising=False)
        # Pass a root with no .sdd/profile
        with pytest.raises(WorkspaceNotInitializedError):
            resolve_profile(root=tmp_path)
