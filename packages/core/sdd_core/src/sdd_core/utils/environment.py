"""
Centralized environment and path utilities for the SDD Framework.
This module serves as the single source of truth for repository structure and artifact paths.
"""

import configparser
import os
import sys
import types
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

SddProfile = Literal["master", "client"]


class WorkspaceNotInitializedError(RuntimeError):
    """Raised when no .sdd/profile is found and no override is provided."""

    def __init__(self, start: Path) -> None:
        super().__init__(
            f"No SDD workspace found from '{start}' up to filesystem root.\n"
            "Run 'sdd init' to initialize a workspace, or use --profile / SDD_PROFILE to override."
        )


@dataclass(frozen=True)
class ProfileContext:
    """Resolved workspace profile context."""

    type: SddProfile
    name: str
    workspace_id: str
    core_hash: str
    root: Path

    @property
    def is_master(self) -> bool:
        """Is Master."""
        return self.type == "master"

    @property
    def is_client(self) -> bool:
        """Is Client."""
        return self.type == "client"

    def as_dict(self) -> dict[str, Any]:
        """As Dict."""
        return {
            "profile": self.type,
            "name": self.name,
            "workspace_id": self.workspace_id,
            "core_hash": self.core_hash,
            "root": self.root,
            "is_master": self.is_master,
            "is_client": self.is_client,
        }


# Support tomli for Python < 3.11, and tomllib for 3.11+
_tomllib_mod: types.ModuleType | None = None
if sys.version_info >= (3, 11):
    import tomllib as _tomllib_mod  # type: ignore[no-redef]
else:
    try:
        import tomli as _tomllib_mod
    except ImportError:
        _tomllib_mod = None
tomllib = _tomllib_mod


def is_repo_root(path: Path) -> bool:
    """Check if a path is the SDD repository root."""
    required = [
        path / "pyproject.toml",
        path / "packages" / "core" / "sdd_core" / "pyproject.toml",
    ]
    try:
        return all(p.exists() for p in required)
    except (PermissionError, OSError):
        # If we can't check due to permission issues, it's not the root
        return False


def detect_repo_root() -> Path:
    """Find the project root by searching from CWD and __file__."""
    # 1. Search from CWD
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if is_repo_root(candidate):
            return candidate

    # 2. Search from current file location (if installed in -e mode)
    file_path: Path | None = None
    try:
        file_path = Path(__file__).resolve()
    except NameError:
        file_path = None

    if file_path is not None:
        for candidate in file_path.parents:
            if is_repo_root(candidate):
                return candidate

    # 3. Fallback for CI/CD environments
    if "GITHUB_WORKSPACE" in os.environ:
        return Path(os.environ["GITHUB_WORKSPACE"]).resolve()

    raise RuntimeError(
        "SDD Project root not found. Ensure you are running from within the repository."
    )


def get_project_config() -> dict[str, Any]:
    """Load configuration from root pyproject.toml."""
    root = detect_repo_root()
    toml_path = root / "pyproject.toml"

    if not tomllib:
        return {}

    try:
        with open(toml_path, "rb") as f:
            loaded = tomllib.load(f)
            return cast(dict[str, Any], loaded)
    except Exception:
        return {}


def get_sdd_paths() -> dict[str, Path]:
    """Resolve standard SDD paths for both framework repo and client workspaces.

    Resolution precedence:
    1. SDD framework repository root (development mode)
    2. Active workspace root containing `.sdd/` (installed CLI mode)
    3. Current working directory (fresh onboarding before `.sdd` exists)
    """
    try:
        root = detect_repo_root()
    except RuntimeError:
        root = find_workspace_root() or Path.cwd().resolve()
    gen = root / "generated"

    # Prefer .sdd/source over generated/client/build/docs-meta when compiling
    source_spec = (
        root / ".sdd" / "source"
        if (root / ".sdd" / "source").exists()
        else gen / "client" / "build" / "docs-meta"
    )

    paths = {
        "root": root,
        "generated": gen,
        # Master (Core Framework) - Immutable artifacts
        "master": gen / "master",
        "master_compiled": gen / "master" / "compiled",
        "master_build": gen / "master" / "build",
        "master_context": gen / "master" / "context",
        # Client (Project Instance) - Mutable/Instance artifacts
        "client": gen / "client",
        "client_compiled": gen / "client" / "compiled",
        "client_build": gen / "client" / "build",
        "client_context": gen / "client" / "context",
        "docs_meta": gen / "client" / "build" / "docs-meta",
        # Source Code & Docs
        "source_spec": source_spec,
        "packages": root / "packages",
        "core_pkg": root / "packages" / "core" / "sdd_core",
        "tools": root / "tools",
        "scripts": root / "scripts",
        # Compatibility aliases
        "compiler_output": gen / "master" / "compiled",
        "wizard_runtime": gen / "client" / "compiled",
    }
    return paths


def resolve_venv_python(venv_dir: Path) -> Path:
    """Locate the python executable within a virtualenv (cross-platform)."""
    linux_python = venv_dir / "bin" / "python"
    if linux_python.exists():
        return linux_python

    windows_python = venv_dir / "Scripts" / "python.exe"
    if windows_python.exists():
        return windows_python

    raise RuntimeError("Could not find virtualenv python executable")


def detect_profile(root: Path | None = None) -> SddProfile:
    """Detect active SDD profile.

    Deprecated: use resolve_profile() for strict no-fallback resolution.
    Kept for backward compat with code that cannot raise on missing workspace.
    """
    try:
        ctx = resolve_profile(root=root)
        return ctx.type
    except WorkspaceNotInitializedError:
        return "client"


def get_profile_context(profile: SddProfile | None = None) -> dict[str, Any]:
    """Return full context dict with profile + paths for use in CLI commands.

    Deprecated: use resolve_profile() which returns a typed ProfileContext.
    """
    try:
        root = detect_repo_root()
    except RuntimeError:
        root = Path.cwd()

    active_profile: SddProfile = profile or detect_profile(root)
    paths = get_sdd_paths()

    return {
        "profile": active_profile,
        "root": root,
        "paths": paths,
        "is_master": active_profile == "master",
        "is_client": active_profile == "client",
    }


def resolve_venv_sdd(venv_dir: Path) -> Path:
    """Locate the sdd entry point within a virtualenv (cross-platform)."""
    linux_sdd = venv_dir / "bin" / "sdd"
    if linux_sdd.exists():
        return linux_sdd

    windows_sdd = venv_dir / "Scripts" / "sdd.exe"
    if windows_sdd.exists():
        return windows_sdd

    raise RuntimeError("Could not find sdd executable in virtualenv")


# ========== WORKSPACE DETECTION (walk-up, .sdd/profile) ==========


def find_workspace_root(start: Path | None = None) -> Path | None:
    """Walk up from start (default: cwd) looking for .sdd/ directory.

    Returns the directory that contains .sdd/, or None if not found.
    This is semantically different from detect_repo_root() — that function
    finds the SDD *development* repo by looking for packages/core/sdd_core/.
    This function finds a user *workspace* initialised with 'sdd init'.
    """
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".sdd").is_dir():
            return candidate
    return None


def resolve_profile(
    root: Path | None = None,
    override: str | None = None,
) -> ProfileContext:
    """Resolve the active workspace profile.

    Resolution order (no silent fallback):
      1. override argument (from --profile flag or SDD_PROFILE env)
      2. SDD_PROFILE environment variable
      3. .sdd/profile file (walk-up from cwd if root is None)
      4. WorkspaceNotInitializedError — explicit, actionable error

    Args:
        root: Explicit workspace root. If None, find_workspace_root() is called.
        override: Profile type override ("master" | "client"). Never written to disk.

    Returns:
        ProfileContext with resolved type, name, workspace_id, core_hash, root.

    Raises:
        WorkspaceNotInitializedError: When no .sdd/profile exists and no override given.
    """
    # 1 + 2: override or env var (runtime-only, never persisted)
    effective_override = (
        override or os.environ.get("SDD_PROFILE", "").strip().lower() or None
    )
    if effective_override in ("master", "client"):
        # We still need a root to anchor paths — best-effort, no error
        workspace_root = root or find_workspace_root() or Path.cwd()
        return ProfileContext(
            type=cast(SddProfile, effective_override),
            name=effective_override,
            workspace_id="",
            core_hash="",
            root=workspace_root,
        )

    # 3: .sdd/profile file
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


def write_profile(root: Path, profile_type: SddProfile, name: str) -> ProfileContext:
    """Write a new .sdd/profile file (used by 'sdd init').

    Creates the .sdd/ directory if needed. Generates a new workspace_id UUID.
    core_hash is left empty — populated by 'sdd governance compile'.
    """
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

    with open(profile_path, "w", encoding="utf-8") as f:
        parser.write(f)

    return ProfileContext(
        type=profile_type,
        name=name,
        workspace_id=workspace_id,
        core_hash="",
        root=root,
    )
