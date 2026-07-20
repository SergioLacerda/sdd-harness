"""Repository-level environment helpers."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from typing import Any, cast

if sys.version_info >= (3, 11):
    import tomllib as _tomllib_mod
else:
    try:
        import tomli as _tomllib_mod
    except ImportError:
        _tomllib_mod = None
tomllib: types.ModuleType | None = _tomllib_mod


def is_repo_root(path: Path) -> bool:
    """Check if a path is the SDD repository root."""
    required = [
        path / "pyproject.toml",
        path / "packages" / "core" / "sdd_core" / "pyproject.toml",
    ]
    try:
        return all(p.exists() for p in required)
    except (PermissionError, OSError):
        return False


def detect_repo_root() -> Path:
    """Find the project root by searching from CWD and `__file__`."""
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if is_repo_root(candidate):
            return candidate

    try:
        file_path = Path(__file__).resolve()
    except NameError:
        file_path = None

    if file_path is not None:
        for candidate in file_path.parents:
            if is_repo_root(candidate):
                return candidate

    if "GITHUB_WORKSPACE" in os.environ:
        return Path(os.environ["GITHUB_WORKSPACE"]).resolve()

    raise RuntimeError(
        "SDD Project root not found. Ensure you are running from within the repository."
    )


def get_project_config() -> dict[str, Any]:
    """Load configuration from the root `pyproject.toml`."""
    root = detect_repo_root()
    toml_path = root / "pyproject.toml"

    if not tomllib:
        return {}

    try:
        with open(toml_path, "rb") as handle:
            loaded = tomllib.load(handle)
            return cast(dict[str, Any], loaded)
    except Exception:
        return {}
