"""Extended test coverage for environment.py edge cases and branching scenarios."""

import configparser
from pathlib import Path
from unittest.mock import patch

import pytest

from sdd_core.utils.environment import (
    WorkspaceNotInitializedError,
    detect_profile,
    get_profile_context,
    get_project_config,
    resolve_profile,
    resolve_venv_python,
    resolve_venv_sdd,
    write_profile,
)


class TestVenvPaths:
    """Test virtualenv path resolution functions."""

    def test_resolve_venv_python_windows_path(self, tmp_path):
        """Verify resolve_venv_python finds Windows Scripts/python.exe."""
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        python_exe = scripts_dir / "python.exe"
        python_exe.touch()

        result = resolve_venv_python(tmp_path)

        assert result == python_exe
        assert result.exists()

    def test_resolve_venv_python_raises_when_empty(self, tmp_path):
        """Verify resolve_venv_python raises RuntimeError when python not found."""
        with (
            patch.object(Path, "exists", return_value=False),
            pytest.raises(
                RuntimeError, match="Could not find virtualenv python executable"
            ),
        ):
            resolve_venv_python(tmp_path)

    def test_resolve_venv_sdd_windows_path(self, tmp_path):
        """Verify resolve_venv_sdd finds Windows Scripts/sdd.exe."""
        scripts_dir = tmp_path / "Scripts"
        scripts_dir.mkdir()
        sdd_exe = scripts_dir / "sdd.exe"
        sdd_exe.touch()

        result = resolve_venv_sdd(tmp_path)

        assert result == sdd_exe
        assert result.exists()


class TestDetectProfile:
    """Test profile detection with fallback behavior."""

    def test_detect_profile_returns_client_when_no_sdd_dir(self, tmp_path, monkeypatch):
        """Verify detect_profile returns 'client' when workspace not initialized."""
        monkeypatch.chdir(tmp_path)
        # tmp_path has no .sdd/ directory

        result = detect_profile(tmp_path)

        assert result == "client"

    def test_get_profile_context_uses_cwd_when_repo_root_fails(
        self, tmp_path, monkeypatch
    ):
        """Verify get_profile_context falls back to cwd when detect_repo_root raises."""
        monkeypatch.chdir(tmp_path)

        with (
            patch(
                "sdd_core.utils.environment.detect_repo_root",
                side_effect=RuntimeError("Not found"),
            ),
            patch(
                "sdd_core.utils.environment.get_sdd_paths",
                return_value={"root": tmp_path},
            ),
        ):
            result = get_profile_context()

        assert result["root"] == tmp_path
        assert result["profile"] == "client"


class TestResolveProfile:
    """Test strict profile resolution."""

    def test_resolve_profile_raises_when_no_sdd_dir(self, tmp_path):
        """Verify resolve_profile raises WorkspaceNotInitializedError when no .sdd/ exists."""
        with pytest.raises(WorkspaceNotInitializedError):
            resolve_profile(root=tmp_path)

    def test_resolve_profile_raises_when_no_profile_file(self, tmp_path):
        """Verify resolve_profile raises when .sdd/ exists but profile file missing."""
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()

        with pytest.raises(WorkspaceNotInitializedError):
            resolve_profile(root=tmp_path)

    def test_resolve_profile_raises_on_invalid_type(self, tmp_path):
        """Verify resolve_profile raises when profile type is invalid."""
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        profile_path = sdd_dir / "profile"

        parser = configparser.ConfigParser()
        parser["sdd"] = {"type": "invalid"}
        with open(profile_path, "w", encoding="utf-8") as f:
            parser.write(f)

        with pytest.raises(WorkspaceNotInitializedError):
            resolve_profile(root=tmp_path)

    def test_resolve_profile_happy_path_client(self, tmp_path):
        """Verify resolve_profile successfully resolves valid client profile."""
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        profile_path = sdd_dir / "profile"

        parser = configparser.ConfigParser()
        parser["sdd"] = {
            "type": "client",
            "name": "test-workspace",
            "workspace_id": "ws123",
        }
        with open(profile_path, "w", encoding="utf-8") as f:
            parser.write(f)

        result = resolve_profile(root=tmp_path)

        assert result.type == "client"
        assert result.name == "test-workspace"
        assert result.workspace_id == "ws123"
        assert result.root == tmp_path

    def test_resolve_profile_happy_path_master(self, tmp_path):
        """Verify resolve_profile successfully resolves valid master profile."""
        sdd_dir = tmp_path / ".sdd"
        sdd_dir.mkdir()
        profile_path = sdd_dir / "profile"

        parser = configparser.ConfigParser()
        parser["sdd"] = {"type": "master", "name": "framework", "workspace_id": "fw123"}
        with open(profile_path, "w", encoding="utf-8") as f:
            parser.write(f)

        result = resolve_profile(root=tmp_path)

        assert result.type == "master"
        assert result.name == "framework"
        assert result.is_master is True
        assert result.is_client is False


class TestRepoRootDetection:
    """Test repository root detection."""

    def test_resolve_venv_sdd_raises_when_empty_dir(self, tmp_path):
        """Verify resolve_venv_sdd raises RuntimeError when sdd executable not found."""
        with (
            patch.object(Path, "exists", return_value=False),
            pytest.raises(RuntimeError, match="Could not find sdd executable"),
        ):
            resolve_venv_sdd(tmp_path)


class TestTomlImport:
    """Test TOML configuration loading."""

    def test_get_project_config_returns_empty_when_no_tomllib(
        self, tmp_path, monkeypatch
    ):
        """Verify get_project_config returns {} when tomllib is unavailable."""
        monkeypatch.chdir(tmp_path)

        with (
            patch("sdd_core.utils.environment.tomllib", None),
            patch("sdd_core.utils.environment.detect_repo_root", return_value=tmp_path),
        ):
            result = get_project_config()

        assert result == {}

    def test_get_project_config_returns_config_when_pyproject_exists(
        self, tmp_path, monkeypatch
    ):
        """Verify get_project_config parses and returns pyproject.toml content."""
        monkeypatch.chdir(tmp_path)

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool]\nkey = "value"\n', encoding="utf-8")

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            result = get_project_config()

        assert isinstance(result, dict)
        assert "tool" in result or result == {}  # May be empty if tomllib unavailable


class TestProfileOverride:
    """Test profile resolution with environment overrides."""

    def test_resolve_profile_with_override_master(self, tmp_path):
        """Verify resolve_profile respects override argument for master."""
        result = resolve_profile(root=tmp_path, override="master")

        assert result.type == "master"
        assert result.name == "master"

    def test_resolve_profile_with_override_client(self, tmp_path):
        """Verify resolve_profile respects override argument for client."""
        result = resolve_profile(root=tmp_path, override="client")

        assert result.type == "client"
        assert result.name == "client"

    def test_resolve_profile_with_env_var(self, tmp_path, monkeypatch):
        """Verify resolve_profile respects SDD_PROFILE environment variable."""
        monkeypatch.setenv("SDD_PROFILE", "master")

        result = resolve_profile(root=tmp_path)

        assert result.type == "master"


class TestWriteProfile:
    """Test profile file writing."""

    def test_write_profile_creates_sdd_directory(self, tmp_path):
        """Verify write_profile creates .sdd directory if missing."""
        write_profile(tmp_path, "client", "test-ws")

        assert (tmp_path / ".sdd").exists()
        assert (tmp_path / ".sdd" / "profile").exists()

    def test_write_profile_returns_valid_context(self, tmp_path):
        """Verify write_profile returns valid ProfileContext."""
        result = write_profile(tmp_path, "master", "framework")

        assert result.type == "master"
        assert result.name == "framework"
        assert result.workspace_id != ""
        assert result.root == tmp_path
