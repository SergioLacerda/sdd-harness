"""sdd init — nested-workspace boundary detection.

Split out of `init.py` (T5,
`.analysis/pending/2026-06-15-sdd-cli-refactoring-pending-followup.md`): pure
path-logic helpers with no dependency on the rest of `init.py`.
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_BOUNDARY_MARKERS = (
    ".git",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Makefile",
)


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _find_project_boundary(cwd: Path) -> Path | None:
    for candidate in [cwd, *cwd.parents]:
        if any((candidate / marker).exists() for marker in _PROJECT_BOUNDARY_MARKERS):
            return candidate
    return None


def _find_parent_workspace_with_profile(start: Path) -> Path | None:
    """Nearest ancestor that is a real workspace (`.sdd/profile` present).

    A bare `.sdd/` directory without a profile — e.g. the `~/.sdd/bin`
    compiler-binary cache — is not a workspace and must not block `sdd init`.
    """
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".sdd" / "profile").is_file():
            return candidate
    return None


def _find_blocking_parent_workspace(cwd: Path) -> Path | None:
    parent_workspace = _find_parent_workspace_with_profile(cwd.parent)
    if parent_workspace is None:
        return None
    if not (parent_workspace / ".sdd" / "profile").exists():
        # A bare `.sdd/` with no profile is a global CLI cache (toolchain
        # binaries, runtime state), not an initialized project workspace.
        return None
    project_boundary = _find_project_boundary(cwd)
    if project_boundary is not None and not _is_relative_to(
        parent_workspace, project_boundary
    ):
        return None
    return parent_workspace
