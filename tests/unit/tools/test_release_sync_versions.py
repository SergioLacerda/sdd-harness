from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.release.resolve_vcs_version import resolve_head_tag
from tools.release.sync_versions import (
    discover_workspace_packages,
    normalize_version,
    sync_version,
)


def _write_package(root: Path, member: str, version: str = "0.0.1") -> None:
    package_dir = root / member
    package_dir.mkdir(parents=True)
    (package_dir / "pyproject.toml").write_text(
        f"""[project]
name = "{package_dir.name.replace("_", "-")}"
version = "{version}"
""",
        encoding="utf-8",
    )


def test_normalize_version_accepts_v_prefixed_git_tags() -> None:
    assert normalize_version("0.1.0") == "0.1.0"
    assert normalize_version("v0.1.0") == "0.1.0"
    assert normalize_version("V0.1.0") == "0.1.0"


def test_resolve_head_tag_uses_governed_process_runner(tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    class _Runner:
        def run(self, args: list[str], **kwargs: object) -> SimpleNamespace:
            calls.append({"args": args, **kwargs})
            return SimpleNamespace(returncode=0, stdout="V0.1.0\n", stderr="")

    assert resolve_head_tag(tmp_path, runner=_Runner()) == "V0.1.0"
    assert calls == [
        {
            "args": ["git", "describe", "--tags", "--exact-match", "HEAD"],
            "cwd": tmp_path,
            "capture_output": True,
        }
    ]


def test_sync_version_updates_all_uv_workspace_members(tmp_path: Path) -> None:
    members = [
        "packages/core/sdd_core",
        "packages/features/sdd_adapters",
        "packages/features/sdd_pages",
        "packages/interfaces/sdd_cli",
    ]
    (tmp_path / "pyproject.toml").write_text(
        """[tool.uv.workspace]
members = [
    "packages/core/sdd_core",
    "packages/features/sdd_adapters",
    "packages/features/sdd_pages",
    "packages/interfaces/sdd_cli",
]
""",
        encoding="utf-8",
    )
    for member in members:
        _write_package(tmp_path, member)

    with pytest.raises(SystemExit) as exc:
        sync_version("V0.1.0", workspace_root=tmp_path)

    assert exc.value.code == 0
    assert discover_workspace_packages(tmp_path) == members
    for member in members:
        content = (tmp_path / member / "pyproject.toml").read_text(encoding="utf-8")
        assert 'version = "0.1.0"' in content


def test_sync_version_succeeds_when_already_at_target_version(tmp_path: Path) -> None:
    """A package already pinned to the target version must not be reported as
    a failure just because re-writing it would be a no-op."""
    members = [
        "packages/core/sdd_core",
        "packages/interfaces/sdd_cli",
    ]
    (tmp_path / "pyproject.toml").write_text(
        """[tool.uv.workspace]
members = [
    "packages/core/sdd_core",
    "packages/interfaces/sdd_cli",
]
""",
        encoding="utf-8",
    )
    # sdd_core is already at the target version; sdd_cli is not.
    _write_package(tmp_path, "packages/core/sdd_core", version="0.1.0")
    _write_package(tmp_path, "packages/interfaces/sdd_cli", version="0.0.9")

    with pytest.raises(SystemExit) as exc:
        sync_version("V0.1.0", workspace_root=tmp_path)

    assert exc.value.code == 0
    for member in members:
        content = (tmp_path / member / "pyproject.toml").read_text(encoding="utf-8")
        assert 'version = "0.1.0"' in content
