"""Workspace and profile resolution helpers."""

from __future__ import annotations

import configparser
import os
import uuid
from pathlib import Path
from typing import cast

from ._environment_models import (
    ProfileContext,
    SddProfile,
    WorkspaceNotInitializedError,
)


def _workspace_root_from_env() -> Path | None:
    raw = os.environ.get("SDD_WORKSPACE_ROOT", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def find_workspace_root(start: Path | None = None) -> Path | None:
    """Walk up from `start` looking for a `.sdd/` directory."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".sdd").is_dir():
            return candidate
    return None


def resolve_venv_python(venv_dir: Path) -> Path:
    linux_python = venv_dir / "bin" / "python"
    if linux_python.exists():
        return linux_python

    windows_python = venv_dir / "Scripts" / "python.exe"
    if windows_python.exists():
        return windows_python

    raise RuntimeError("Could not find virtualenv python executable")


def resolve_venv_sdd(venv_dir: Path) -> Path:
    linux_sdd = venv_dir / "bin" / "sdd"
    if linux_sdd.exists():
        return linux_sdd

    windows_sdd = venv_dir / "Scripts" / "sdd.exe"
    if windows_sdd.exists():
        return windows_sdd

    raise RuntimeError("Could not find sdd executable in virtualenv")


def resolve_profile(
    root: Path | None = None,
    override: str | None = None,
) -> ProfileContext:
    """Resolve the active workspace profile with no silent fallback."""
    effective_override = (
        override or os.environ.get("SDD_PROFILE", "").strip().lower() or None
    )
    if effective_override in ("master", "client"):
        workspace_root = root or find_workspace_root() or Path.cwd()
        return ProfileContext(
            type=cast(SddProfile, effective_override),
            name=effective_override,
            workspace_id="",
            core_hash="",
            root=workspace_root,
        )

    workspace_root = root or find_workspace_root() or Path.cwd()
    if (root is None) and (find_workspace_root() is None):
        raise WorkspaceNotInitializedError(Path.cwd())

    profile_path = workspace_root / ".sdd" / "profile"
    if not profile_path.exists():
        raise WorkspaceNotInitializedError(workspace_root)

    parser = configparser.ConfigParser()
    parser.read(profile_path)
    raw_type = parser.get("sdd", "type", fallback="").strip().lower()
    if raw_type not in ("master", "client"):
        raise WorkspaceNotInitializedError(workspace_root)

    return ProfileContext(
        type=cast(SddProfile, raw_type),
        name=parser.get("sdd", "name", fallback=raw_type),
        workspace_id=parser.get("sdd", "workspace_id", fallback=""),
        core_hash=parser.get("sdd", "core_hash", fallback=""),
        root=workspace_root,
    )


def detect_profile(root: Path | None = None) -> SddProfile:
    try:
        return resolve_profile(root=root).type
    except WorkspaceNotInitializedError:
        return "client"


def write_profile(root: Path, profile_type: SddProfile, name: str) -> ProfileContext:
    sdd_dir = root / ".sdd"
    sdd_dir.mkdir(parents=True, exist_ok=True)
    workspace_id = str(uuid.uuid4())
    profile_path = sdd_dir / "profile"

    parser = configparser.ConfigParser()
    parser["sdd"] = {
        "version": "1",
        "workspace_id": workspace_id,
        "type": profile_type,
        "name": name,
        "core_hash": "",
    }
    with open(profile_path, "w", encoding="utf-8") as handle:
        parser.write(handle)

    return ProfileContext(
        type=profile_type,
        name=name,
        workspace_id=workspace_id,
        core_hash="",
        root=root,
    )
