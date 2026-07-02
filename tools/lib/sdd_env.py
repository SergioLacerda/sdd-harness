"""Environment utilities for tools scripts."""

from pathlib import Path


def detect_repo_root() -> Path:
    """Detect the repository root directory."""
    try:
        from sdd_core.utils.environment import detect_repo_root as _detect

        return _detect()
    except ImportError:
        # Fallback: search for .sdd directory
        current = Path.cwd()
        for parent in [current, *current.parents]:
            if (parent / ".sdd").exists():
                return parent
        return Path.cwd()


def get_sdd_paths() -> dict[str, Path]:
    """Get SDD-related directory paths."""
    try:
        from sdd_core.utils.environment import get_sdd_paths as _get

        return _get()
    except ImportError:
        root = detect_repo_root()
        gen = root / "generated"
        return {
            "repo_root": root,
            "master_compiled": gen / "master" / "compiled",
            "client_compiled": gen / "client" / "compiled",
            "client_build": gen / "client" / "build",
        }
