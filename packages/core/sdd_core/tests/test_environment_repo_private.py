from __future__ import annotations

import builtins
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from sdd_core.utils import _environment_repo as env_repo


def test_is_repo_root_true_and_false(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").touch()
    core = tmp_path / "packages" / "core" / "sdd_core"
    core.mkdir(parents=True)
    (core / "pyproject.toml").touch()
    assert env_repo.is_repo_root(tmp_path) is True
    (core / "pyproject.toml").unlink()
    assert env_repo.is_repo_root(tmp_path) is False


def test_detect_repo_root_prefers_cwd(tmp_path: Path) -> None:
    with (
        patch.object(Path, "cwd", return_value=tmp_path),
        patch(
            "sdd_core.utils._environment_repo.is_repo_root",
            side_effect=lambda p: p == tmp_path,
        ),
    ):
        assert env_repo.detect_repo_root() == tmp_path


def test_detect_repo_root_uses_file_parents_when_cwd_fails(tmp_path: Path) -> None:
    fake_file = tmp_path / "pkg" / "module.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("", encoding="utf-8")
    with (
        patch.object(Path, "cwd", return_value=tmp_path / "elsewhere"),
        patch(
            "sdd_core.utils._environment_repo.is_repo_root",
            side_effect=lambda p: p == tmp_path,
        ),
        patch("sdd_core.utils._environment_repo.__file__", str(fake_file)),
    ):
        assert env_repo.detect_repo_root() == tmp_path


def test_detect_repo_root_uses_github_workspace(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    with (
        patch("sdd_core.utils._environment_repo.is_repo_root", return_value=False),
        patch.object(Path, "cwd", return_value=tmp_path / "nowhere"),
        patch("sdd_core.utils._environment_repo.__file__", str(tmp_path / "x.py")),
    ):
        assert env_repo.detect_repo_root() == tmp_path.resolve()


def test_detect_repo_root_raises_when_not_found(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
    with (
        patch("sdd_core.utils._environment_repo.is_repo_root", return_value=False),
        patch.object(Path, "cwd", return_value=tmp_path),
        patch("sdd_core.utils._environment_repo.__file__", str(tmp_path / "x.py")),
        pytest.raises(RuntimeError, match="SDD Project root not found"),
    ):
        env_repo.detect_repo_root()


def test_get_project_config_handles_tomllib_absent(tmp_path: Path) -> None:
    with (
        patch(
            "sdd_core.utils._environment_repo.detect_repo_root", return_value=tmp_path
        ),
        patch("sdd_core.utils._environment_repo.tomllib", None),
    ):
        assert env_repo.get_project_config() == {}


def test_get_project_config_reads_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='demo'\n", encoding="utf-8"
    )
    with patch(
        "sdd_core.utils._environment_repo.detect_repo_root", return_value=tmp_path
    ):
        config = env_repo.get_project_config()
    assert config["project"]["name"] == "demo"


def test_get_project_config_returns_empty_on_parse_error(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project\n", encoding="utf-8")
    with patch(
        "sdd_core.utils._environment_repo.detect_repo_root", return_value=tmp_path
    ):
        assert env_repo.get_project_config() == {}


def test_is_repo_root_returns_false_on_os_error(tmp_path: Path) -> None:
    with patch("pathlib.Path.exists", side_effect=OSError("denied")):
        assert env_repo.is_repo_root(tmp_path) is False


def test_detect_repo_root_handles_missing___file__(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
    monkeypatch.delattr(env_repo, "__file__", raising=False)
    with (
        patch.object(Path, "cwd", return_value=tmp_path),
        patch("sdd_core.utils._environment_repo.is_repo_root", return_value=False),
        pytest.raises(RuntimeError, match="SDD Project root not found"),
    ):
        env_repo.detect_repo_root()


def test_detect_repo_root_returns_from___file___parents(tmp_path: Path) -> None:
    fake_file = tmp_path / "nested" / "pkg" / "module.py"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_text("", encoding="utf-8")
    with (
        patch.object(Path, "cwd", return_value=tmp_path / "cwd"),
        patch("sdd_core.utils._environment_repo.__file__", str(fake_file)),
        patch(
            "sdd_core.utils._environment_repo.is_repo_root",
            side_effect=lambda p: p == tmp_path,
        ),
    ):
        assert env_repo.detect_repo_root() == tmp_path


def test_module_import_sets_tomllib_none_when_tomli_missing(tmp_path: Path) -> None:
    module_path = Path(env_repo.__file__)
    spec = importlib.util.spec_from_file_location("test_env_repo_no_tomli", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    original_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "tomli":
            raise ImportError("missing tomli")
        return original_import(name, globals, locals, fromlist, level)

    with (
        patch.object(sys, "version_info", (3, 10, 0)),
        patch("builtins.__import__", side_effect=_fake_import),
    ):
        spec.loader.exec_module(module)

    assert module.tomllib is None
