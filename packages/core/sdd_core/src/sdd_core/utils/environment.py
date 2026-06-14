"""Public facade for environment and workspace helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

from sdd_core.utils._environment_models import (
    ProfileContext,
    SddProfile,
    WorkspaceNotInitializedError,
)
from sdd_core.utils._environment_repo import (
    is_repo_root,
    tomllib,
)
from sdd_core.utils._environment_workspace import (
    _workspace_root_from_env as _workspace_root_from_env_impl,
)
from sdd_core.utils._environment_workspace import (
    detect_profile,
    find_workspace_root,
    resolve_profile,
    resolve_venv_python,
    resolve_venv_sdd,
    write_profile,
)


def detect_repo_root() -> Path:
    """Detect the current repository root."""
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if is_repo_root(candidate):
            return candidate
    if "GITHUB_WORKSPACE" in os.environ:
        return Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    raise RuntimeError(
        "SDD Project root not found. Ensure you are running from within the repository."
    )


def get_project_config() -> dict[str, Any]:
    """Load the root `pyproject.toml` when available."""
    if not tomllib:
        return {}
    try:
        with open(detect_repo_root() / "pyproject.toml", "rb") as handle:
            return cast(dict[str, Any], tomllib.load(handle))
    except Exception:
        return {}


def _workspace_root_from_env() -> Path | None:
    return _workspace_root_from_env_impl()


def get_sdd_paths(
    *, repo_root: Path | None = None, workspace_root: Path | None = None
) -> dict[str, Path]:
    """Resolve canonical SDD paths for the active workspace."""
    try:
        resolved_repo_root = repo_root.resolve() if repo_root else detect_repo_root()
    except RuntimeError:
        resolved_repo_root = Path.cwd().resolve()
    env_workspace = _workspace_root_from_env()
    resolved_workspace_root = (
        workspace_root.resolve()
        if workspace_root
        else env_workspace or find_workspace_root() or resolved_repo_root
    )
    generated = resolved_workspace_root / "generated"
    isolated = bool(env_workspace) and os.environ.get(
        "SDD_TEST_ISOLATED_WORKSPACE", ""
    ).strip().lower() in {"1", "true", "yes", "on"}
    source_spec = (
        resolved_workspace_root / ".sdd" / "source"
        if not isolated and (resolved_workspace_root / ".sdd" / "source").exists()
        else generated / "client" / "build" / "docs-meta"
    )
    return {
        "root": resolved_workspace_root,
        "repo_root": resolved_repo_root,
        "workspace_root": resolved_workspace_root,
        "generated": generated,
        "master": generated / "master",
        "master_compiled": generated / "master" / "compiled",
        "master_build": generated / "master" / "build",
        "master_context": generated / "master" / "context",
        "client": generated / "client",
        "client_compiled": generated / "client" / "compiled",
        "client_build": generated / "client" / "build",
        "client_context": generated / "client" / "context",
        "docs_meta": generated / "client" / "build" / "docs-meta",
        "source_spec": source_spec,
        "packages": resolved_repo_root / "packages",
        "core_pkg": resolved_repo_root / "packages" / "core" / "sdd_core",
        "tools": resolved_repo_root / "tools",
        "scripts": resolved_repo_root / "scripts",
        "compiler_output": generated / "master" / "compiled",
        "wizard_runtime": generated / "client" / "compiled",
    }


def get_profile_context(profile: SddProfile | None = None) -> dict[str, Any]:
    """Build a lightweight profile context payload."""
    try:
        root = detect_repo_root()
    except RuntimeError:
        root = Path.cwd()
    active_profile = profile or detect_profile(root)
    return {
        "profile": active_profile,
        "root": root,
        "paths": get_sdd_paths(),
        "is_master": active_profile == "master",
        "is_client": active_profile == "client",
    }


__all__ = [
    "ProfileContext",
    "SddProfile",
    "WorkspaceNotInitializedError",
    "detect_profile",
    "detect_repo_root",
    "find_workspace_root",
    "get_profile_context",
    "get_project_config",
    "get_sdd_paths",
    "is_repo_root",
    "resolve_profile",
    "resolve_venv_python",
    "resolve_venv_sdd",
    "tomllib",
    "write_profile",
]
