"""Pure helpers for reading and checking governance configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _workspace_root_from_governance_path(path: str) -> Path:
    """Best-effort workspace root resolution from a governance path."""
    resolved = Path(path).resolve()
    if resolved.name == "compiled" and resolved.parent.name == ".sdd":
        return resolved.parent.parent
    if resolved.name == ".sdd":
        return resolved.parent
    return resolved.parent


def check_files_accessible(path: str) -> bool:
    """Check if all required governance files are accessible."""
    from sdd_cli.utils.loader import validate_governance_path

    return validate_governance_path(path)


def check_fingerprints_valid(config: dict[str, Any] | None) -> bool:
    """Check if governance fingerprints are valid."""
    try:
        if config is None:
            return False
        return (
            config.get("core_fingerprint") is not None
            and config.get("client_fingerprint") is not None
        )
    except Exception:
        return False


def check_no_conflicts(config: dict[str, Any] | None) -> bool:
    """Check for conflicts in governance configuration."""
    try:
        if config is None:
            return False
        return config.get("core_fingerprint") != config.get("client_fingerprint")
    except Exception:
        return False
