"""Shared compliance telemetry path resolution."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_compliance_events_path(*, workspace_root: Path | None = None) -> Path:
    """Resolve compliance JSONL path with optional environment override.

    Env override:
    - ``SDD_COMPLIANCE_EVENTS_PATH``: absolute or cwd-relative path.
    """
    override = os.environ.get("SDD_COMPLIANCE_EVENTS_PATH", "").strip()
    if override:
        candidate = Path(override).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return candidate

    root = workspace_root or Path.cwd()
    return root / ".sdd" / "runtime" / "compliance-events.jsonl"
