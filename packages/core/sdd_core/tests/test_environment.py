"""Unit tests for environment and path utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from sdd_core.utils.environment import (
    ProfileContext,
    WorkspaceNotInitializedError,
    detect_repo_root,
    get_project_config,
    get_sdd_paths,
    is_repo_root,
)

pytestmark = pytest.mark.unit


class TestIsRepoRoot:
    """Tests for is_repo_root detection."""

    def test_valid_repo_root(self, tmp_path: Path) -> None:
        """Should recognize valid repo root with required files."""
        (tmp_path / "pyproject.toml").touch()
        core_path = tmp_path / "packages" / "core" / "sdd_core"
        core_path.mkdir(parents=True)
        (core_path / "pyproject.toml").touch()

        assert is_repo_root(tmp_path) is True

    def test_missing_root_pyproject(self, tmp_path: Path) -> None:
        """Should reject when root pyproject.toml missing."""
        core_path = tmp_path / "packages" / "core" / "sdd_core"
        core_path.mkdir(parents=True)
        (core_path / "pyproject.toml").touch()

        assert is_repo_root(tmp_path) is False

    def test_missing_core_pyproject(self, tmp_path: Path) -> None:
        """Should reject when core pyproject.toml missing."""
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "packages" / "core" / "sdd_core").mkdir(parents=True)

        assert is_repo_root(tmp_path) is False

    def test_handles_permission_errors(self, tmp_path: Path) -> None:
        """Should return False on permission errors."""
        with patch("pathlib.Path.exists", side_effect=PermissionError):
            assert is_repo_root(tmp_path) is False


class TestDetectRepoRoot:
    """Tests for repo root detection."""

    def test_detects_from_cwd(self, tmp_path: Path, monkeypatch) -> None:
        """Should detect repo root from current directory."""
        (tmp_path / "pyproject.toml").touch()
        core_path = tmp_path / "packages" / "core" / "sdd_core"
        core_path.mkdir(parents=True)
        (core_path / "pyproject.toml").touch()

        monkeypatch.chdir(tmp_path)
        with patch("sdd_core.utils.environment.is_repo_root", return_value=True):
            root = detect_repo_root()
            assert isinstance(root, Path)

    def test_detects_from_parent_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Should detect repo root from parent directory."""
        (tmp_path / "pyproject.toml").touch()
        core_path = tmp_path / "packages" / "core" / "sdd_core"
        core_path.mkdir(parents=True)
        (core_path / "pyproject.toml").touch()

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        with patch("sdd_core.utils.environment.is_repo_root") as mock_is_root:
            mock_is_root.side_effect = lambda p: p == tmp_path
            root = detect_repo_root()
            assert root == tmp_path

    def test_detects_from_github_workspace(self, monkeypatch) -> None:
        """Should use GITHUB_WORKSPACE in CI environments."""
        gh_workspace = "/github/workspace"
        monkeypatch.setenv("GITHUB_WORKSPACE", gh_workspace)

        with patch("sdd_core.utils.environment.is_repo_root", return_value=False):
            root = detect_repo_root()
            assert root == Path(gh_workspace).resolve()

    def test_raises_when_not_found(self, monkeypatch) -> None:
        """Should raise when repo root cannot be found."""
        monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)

        with (
            patch("sdd_core.utils.environment.is_repo_root", return_value=False),
            patch("pathlib.Path.parents", []),
            pytest.raises(RuntimeError, match="Project root not found"),
        ):
            detect_repo_root()


class TestProfileContext:
    """Tests for ProfileContext dataclass."""

    def test_profile_context_creation(self) -> None:
        """Should create ProfileContext with required fields."""
        ctx = ProfileContext(
            type="master",
            name="primary",
            workspace_id="ws-123",
            core_hash="abc123",
            root=Path("/tmp"),
        )
        assert ctx.type == "master"
        assert ctx.name == "primary"
        assert ctx.workspace_id == "ws-123"

    def test_is_master_property(self) -> None:
        """Should correctly identify master profile."""
        master_ctx = ProfileContext(
            type="master",
            name="master",
            workspace_id="ws-1",
            core_hash="hash1",
            root=Path("/tmp"),
        )
        assert master_ctx.is_master is True
        assert master_ctx.is_client is False

    def test_is_client_property(self) -> None:
        """Should correctly identify client profile."""
        client_ctx = ProfileContext(
            type="client",
            name="client",
            workspace_id="ws-2",
            core_hash="hash2",
            root=Path("/tmp"),
        )
        assert client_ctx.is_client is True
        assert client_ctx.is_master is False

    def test_as_dict_conversion(self) -> None:
        """Should convert ProfileContext to dict."""
        ctx = ProfileContext(
            type="master",
            name="test",
            workspace_id="ws-1",
            core_hash="hash",
            root=Path("/tmp"),
        )
        data = ctx.as_dict()
        assert data["profile"] == "master"
        assert data["name"] == "test"
        assert data["is_master"] is True


class TestGetProjectConfig:
    """Tests for project configuration loading."""

    def test_loads_pyproject_toml(self, tmp_path: Path) -> None:
        """Should load pyproject.toml when available."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test-project"\n', encoding="utf-8")

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            config = get_project_config()
            assert isinstance(config, dict)

    def test_returns_empty_dict_when_missing(self, tmp_path: Path) -> None:
        """Should return empty dict when pyproject.toml not found."""
        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            config = get_project_config()
            assert config == {}

    def test_returns_empty_dict_on_parse_error(self, tmp_path: Path) -> None:
        """Should return empty dict on TOML parse errors."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("invalid toml content {{{", encoding="utf-8")

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            config = get_project_config()
            assert config == {}


class TestGetSddPaths:
    """Tests for SDD path resolution."""

    def test_returns_all_required_paths(self, tmp_path: Path) -> None:
        """Should return dict with all required paths."""
        (tmp_path / "generated").mkdir()

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=tmp_path
        ):
            paths = get_sdd_paths()

            required_keys = [
                "root",
                "master",
                "master_compiled",
                "master_build",
                "client",
                "client_compiled",
                "source_spec",
            ]
            for key in required_keys:
                assert key in paths
                assert isinstance(paths[key], Path)

    def test_root_path_is_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should set root path correctly."""
        (tmp_path / "generated").mkdir()
        monkeypatch.delenv("SDD_WORKSPACE_ROOT", raising=False)
        with (
            patch("sdd_core.utils.environment.find_workspace_root", return_value=None),
            patch("sdd_core.utils.environment.detect_repo_root", return_value=tmp_path),
        ):
            paths = get_sdd_paths()
            assert paths["root"] == tmp_path

    def test_prefers_sdd_source_over_generated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should prefer .sdd/source when it exists."""
        gen = tmp_path / "generated"
        gen.mkdir()
        monkeypatch.delenv("SDD_WORKSPACE_ROOT", raising=False)

        sdd_source = tmp_path / ".sdd" / "source"
        sdd_source.mkdir(parents=True)

        with (
            patch("sdd_core.utils.environment.find_workspace_root", return_value=None),
            patch("sdd_core.utils.environment.detect_repo_root", return_value=tmp_path),
        ):
            paths = get_sdd_paths()
            assert paths["source_spec"] == sdd_source

    def test_falls_back_to_workspace_root_when_repo_root_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should use workspace root when framework repo root is unavailable."""
        workspace_root = tmp_path / "client-project"
        (workspace_root / ".sdd" / "source").mkdir(parents=True)
        monkeypatch.delenv("SDD_WORKSPACE_ROOT", raising=False)

        with (
            patch(
                "sdd_core.utils.environment.detect_repo_root",
                side_effect=RuntimeError("repo root missing"),
            ),
            patch(
                "sdd_core.utils.environment.find_workspace_root",
                return_value=workspace_root,
            ),
        ):
            paths = get_sdd_paths()
            assert paths["root"] == workspace_root
            assert paths["source_spec"] == workspace_root / ".sdd" / "source"

    def test_falls_back_to_cwd_when_repo_and_workspace_missing(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Should use cwd for onboarding flows before `.sdd` exists."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("SDD_WORKSPACE_ROOT", raising=False)

        with (
            patch(
                "sdd_core.utils.environment.detect_repo_root",
                side_effect=RuntimeError("repo root missing"),
            ),
            patch("sdd_core.utils.environment.find_workspace_root", return_value=None),
        ):
            paths = get_sdd_paths()
            assert paths["root"] == tmp_path.resolve()
            assert (
                paths["source_spec"]
                == tmp_path / "generated" / "client" / "build" / "docs-meta"
            )

    def test_isolated_workspace_root_uses_env_generated_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should isolate generated artifacts under SDD_WORKSPACE_ROOT in tests."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        workspace_root = tmp_path / "shadow-workspace"
        monkeypatch.setenv("SDD_WORKSPACE_ROOT", str(workspace_root))

        with patch(
            "sdd_core.utils.environment.detect_repo_root", return_value=repo_root
        ):
            paths = get_sdd_paths()
            assert paths["root"] == workspace_root.resolve()
            assert paths["repo_root"] == repo_root
            assert paths["generated"] == workspace_root / "generated"
            assert (
                paths["source_spec"]
                == workspace_root / "generated" / "client" / "build" / "docs-meta"
            )


class TestWorkspaceNotInitializedError:
    """Tests for workspace initialization error."""

    def test_error_message_includes_path(self) -> None:
        """Error message should include the start path."""
        start = Path("/tmp/test")
        error = WorkspaceNotInitializedError(start)

        assert str(start) in str(error)

    def test_error_suggests_sdd_init(self) -> None:
        """Error message should suggest running sdd init."""
        error = WorkspaceNotInitializedError(Path("/tmp"))

        assert "sdd init" in str(error)

    def test_error_suggests_profile_override(self) -> None:
        """Error message should mention --profile override."""
        error = WorkspaceNotInitializedError(Path("/tmp"))

        assert "--profile" in str(error) or "SDD_PROFILE" in str(error)
