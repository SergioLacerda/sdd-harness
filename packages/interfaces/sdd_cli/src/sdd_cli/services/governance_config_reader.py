"""Pure helpers for reading and checking governance configuration."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_ROOT_SEED_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
_FINGERPRINT_HEADER_RE = re.compile(r"Governance fingerprint:\s*([0-9a-fA-F]+)")


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


def check_root_seed_drift(path: str) -> tuple[bool, str]:
    """Compare the fingerprint header embedded in root seed files against metadata.json.

    Root seed files (AGENTS.md, CLAUDE.md, GEMINI.md) each carry a
    `Governance fingerprint: <value>` header written at generation time. This
    check re-reads that header and compares it against the workspace's current
    `.sdd/metadata.json` fingerprint, independent of `sdd ask`'s in-session
    `check_fingerprint_drift` (which compares cached runtime state, not
    installed root files against source metadata).
    """
    workspace_root = _workspace_root_from_governance_path(path)
    metadata_file = workspace_root / ".sdd" / "metadata.json"
    if not metadata_file.exists():
        return True, "metadata.json not found — skipping root-seed drift check"

    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except Exception:
        return True, "metadata.json unreadable — skipping root-seed drift check"

    expected_fingerprint = metadata.get("governance_fingerprint") or metadata.get(
        "fingerprints", {}
    ).get("combined")
    if not expected_fingerprint:
        return (
            True,
            "no governance_fingerprint in metadata.json — skipping root-seed drift check",
        )

    drifted: list[str] = []
    for filename in _ROOT_SEED_FILES:
        seed_file = workspace_root / filename
        if not seed_file.exists():
            continue
        try:
            content = seed_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        match = _FINGERPRINT_HEADER_RE.search(content)
        if match and match.group(1) != expected_fingerprint:
            drifted.append(filename)

    if drifted:
        return False, f"root-seed fingerprint drift in: {', '.join(drifted)}"
    return True, "no root-seed drift detected"
