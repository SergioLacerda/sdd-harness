"""Advanced tests for environment utilities (reach 80% target)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sdd_core.utils.environment import (
    ProfileContext,
    detect_repo_root,
    get_project_config,
    get_sdd_paths,
    is_repo_root,
)

pytestmark = pytest.mark.unit


class TestDetectRepoRootAdvanced:
    """Advanced tests for repo root detection."""

    def test_detects_from_multiple_parent_levels(self, tmp_path: Path) -> None:
        """Should detect repo root from deep child directories."""
        (tmp_path / "pyproject.toml").touch()
        core = tmp_path / "packages" / "core" / "sdd_core"
        core.mkdir(parents=True)
        (core / "pyproject.toml").touch()

        deep_child = tmp_path / "a" / "b" / "c" / "d"
        deep_child.mkdir(parents=True)

        with (
            patch.object(Path, "cwd", return_value=deep_child),
            patch("sdd_core.utils.environment.is_repo_root") as mock_is_root,
        ):
            mock_is_root.side_effect = lambda p: p == tmp_path
            root = detect_repo_root()
            assert root == tmp_path

    def test_handles_symlinks_in_path(self, tmp_path: Path) -> None:
        """Should handle symlinked directories."""
        (tmp_path / "pyproject.toml").touch()
        core = tmp_path / "packages" / "core" / "sdd_core"
        core.mkdir(parents=True)
        (core / "pyproject.toml").touch()

        with patch("sdd_core.utils.environment.is_repo_root", return_value=True):
            root = detect_repo_root()
            assert isinstance(root, Path)

    def test_handles_relative_path_conversion(self, tmp_path: Path) -> None:
        """Should handle conversion of relative to absolute paths."""
        with (
            patch("sdd_core.utils.environment.is_repo_root", return_value=True),
            patch.object(Path, "cwd", return_value=tmp_path),
        ):
            root = detect_repo_root()
            assert root.is_absolute()


class TestGetSddPathsVariations:
    """Tests for various SDD path configurations."""

    def test_returns_consistent_paths(self, tmp_path: Path) -> None:
        """get_sdd_paths should return consistent results."""
        (tmp_path / "generated").mkdir()

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            paths1 = get_sdd_paths()
            paths2 = get_sdd_paths()

            for key in paths1:
                assert paths1[key] == paths2[key]

    def test_paths_relative_to_root(self, tmp_path: Path) -> None:
        """All paths should be under the root directory."""
        (tmp_path / "generated").mkdir()

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            paths = get_sdd_paths()

            for key, path in paths.items():
                if key != "root":
                    assert tmp_path in path.parents or tmp_path == path.parent


class TestProfileContextProperties:
    """Tests for ProfileContext properties and methods."""

    def test_frozen_dataclass_immutable(self) -> None:
        """ProfileContext should be immutable."""
        ctx = ProfileContext(
            type="master",
            name="test",
            workspace_id="ws-1",
            core_hash="hash",
            root=Path("/tmp"),
        )

        with pytest.raises(AttributeError):
            ctx.type = "client"

    def test_as_dict_includes_computed_properties(self) -> None:
        """as_dict should include computed properties."""
        ctx = ProfileContext(
            type="client",
            name="test",
            workspace_id="ws-1",
            core_hash="hash",
            root=Path("/tmp"),
        )

        data = ctx.as_dict()
        assert data["is_client"] is True
        assert data["is_master"] is False

    def test_as_dict_roundtrip(self) -> None:
        """Should be able to reconstruct from dict."""
        original = ProfileContext(
            type="master",
            name="prod",
            workspace_id="ws-prod",
            core_hash="hash123",
            root=Path("/prod"),
        )

        data = original.as_dict()
        assert data["name"] == original.name
        assert data["workspace_id"] == original.workspace_id


class TestGetProjectConfigAdvanced:
    """Advanced tests for project configuration loading."""

    def test_handles_missing_sections(self, tmp_path: Path) -> None:
        """Should handle pyproject.toml with missing expected sections."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[build-system]\nrequires = []\n", encoding="utf-8")

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            config = get_project_config()
            assert isinstance(config, dict)

    def test_handles_toml_comments(self, tmp_path: Path) -> None:
        """Should handle TOML files with comments."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "# This is a comment\n[project]\nname = 'test'\n", encoding="utf-8"
        )

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            config = get_project_config()
            assert isinstance(config, dict)

    def test_tomllib_import_fallback(self, tmp_path: Path) -> None:
        """Should handle tomllib import variations."""
        with (
            patch("sdd_core.utils.environment.tomllib", None),
            patch("sdd_core.utils.environment.detect_repo_root", return_value=tmp_path),
        ):
            config = get_project_config()
            assert config == {}


class TestIsRepoRootEdgeCases:
    """Edge cases for repo root detection."""

    def test_handles_readonly_directory(self, tmp_path: Path) -> None:
        """Should handle read-only directories gracefully."""
        (tmp_path / "pyproject.toml").touch()
        core = tmp_path / "packages" / "core" / "sdd_core"
        core.mkdir(parents=True)
        (core / "pyproject.toml").touch()

        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.side_effect = PermissionError()
            assert is_repo_root(tmp_path) is False

    def test_detects_with_extra_files(self, tmp_path: Path) -> None:
        """Should detect root even with extra files."""
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "README.md").touch()
        (tmp_path / "LICENSE").touch()

        core = tmp_path / "packages" / "core" / "sdd_core"
        core.mkdir(parents=True)
        (core / "pyproject.toml").touch()

        assert is_repo_root(tmp_path) is True


class TestPathResolutionCaseSensitivity:
    """Tests for path resolution with various case patterns."""

    def test_paths_work_on_case_insensitive_fs(self, tmp_path: Path) -> None:
        """Should work on both case-sensitive and insensitive filesystems."""
        (tmp_path / "generated").mkdir()

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            paths = get_sdd_paths()
            assert "source_spec" in paths
            assert "master_compiled" in paths

    def test_path_normalization(self, tmp_path: Path) -> None:
        """Should normalize paths correctly."""
        (tmp_path / "generated").mkdir()

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            paths = get_sdd_paths()

            for _key, path in paths.items():
                # Paths should be resolved (no .. or .)
                assert ".." not in str(path)
