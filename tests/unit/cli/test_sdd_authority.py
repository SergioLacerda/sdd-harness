from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_paths_resolve_from_workspace_root(tmp_path: Path) -> None:
    from sdd_cli.utils.sdd_authority import (
        compiled_active_dir,
        enforce_path_policy,
        profile_active_path,
        resolve_workspace_root,
        source_semantic_dir,
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.delenv("SDD_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("SDD_TEST_ISOLATED_WORKSPACE", raising=False)
    try:
        assert resolve_workspace_root(tmp_path) == tmp_path
        assert compiled_active_dir(tmp_path) == tmp_path / ".sdd" / "compiled"
        assert source_semantic_dir(tmp_path) == tmp_path / ".sdd" / "source"
        assert profile_active_path(tmp_path) == tmp_path / ".sdd" / "profile"
        assert (
            enforce_path_policy(
                tmp_path, workspace_root=tmp_path, mode="extraordinary_audit"
            )
            == tmp_path
        )
    finally:
        monkeypatch.undo()


def test_env_workspace_root_applies_when_no_explicit_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sdd_cli.utils.sdd_authority import compiled_active_dir, resolve_workspace_root

    isolated = tmp_path / "isolated"
    monkeypatch.setenv("SDD_WORKSPACE_ROOT", str(isolated))

    assert resolve_workspace_root() == isolated.resolve()
    assert compiled_active_dir() == isolated.resolve() / ".sdd" / "compiled"
