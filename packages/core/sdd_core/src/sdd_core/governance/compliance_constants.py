"""Compliance event type constants and utilities."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Event type constants
COMMAND_INVOKED = "COMMAND_INVOKED"
GOVERNANCE_CHECKED = "GOVERNANCE_CHECKED"
WORKSPACE_INIT = "WORKSPACE_INIT"
COMPILE_COMPLETE = "COMPILE_COMPLETE"
VIOLATION = "VIOLATION"
ASK_COMMAND = "ASK_COMMAND"
ASK_FULL_COMMAND = "ASK_FULL_COMMAND"

_COMPLIANCE_LOG_DISABLED = "disabled"


def default_log_path(workspace_root: Path | None = None) -> Path | None:
    """Resolve JSONL path, respecting SDD_COMPLIANCE_LOG env var.

    Returns None when SDD_COMPLIANCE_LOG=disabled, which suppresses all writes.
    Set SDD_COMPLIANCE_LOG=/path/to/file.jsonl to override the default location.
    """
    env_override = os.environ.get("SDD_COMPLIANCE_LOG", "").strip()
    if env_override.lower() == _COMPLIANCE_LOG_DISABLED:
        return None
    if env_override:
        return Path(env_override)

    root = workspace_root
    if root is None:
        try:
            from sdd_core.utils.environment import find_workspace_root

            root = find_workspace_root()
        except Exception as exc:
            logger.debug(
                "Could not resolve workspace root for compliance log path: %s", exc
            )
    if root is None:
        root = Path.cwd()
    return root / ".sdd" / "runtime" / "compliance-events.jsonl"
