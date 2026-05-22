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
