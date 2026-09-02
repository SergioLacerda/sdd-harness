"""Shared `governance-state.json` read/write cache for `sdd ask` runtime modules.

Split out of `ask_context.py`: `ask_context_drift`, `ask_context_routing`, and
`ask_context_snapshot` all need this cache but `ask_context` itself does not,
and `ask_context_drift` importing it from `ask_context` created a cycle once
`ask_context` needed `ask_context_drift` in turn.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STATE_CACHE: dict[str, dict[str, Any]] = {}


def _load_governance_state(workspace_root: Path) -> dict[str, Any]:
    """Read+parse `governance-state.json` at most once per process per workspace.

    `check_fingerprint_drift`, `write_runtime_cache`, `_read_runtime_state`,
    `store_routing_decision`, and `write_runtime_cache_and_routing_decision`
    all share this cache so a single `sdd ask` call does one disk read of
    this file instead of one per call site (design.md D-01). Only a
    successful write via `_store_governance_state` may refresh a cache entry.
    """
    key = str(workspace_root.resolve())
    cached = _STATE_CACHE.get(key)
    if cached is not None:
        return cached
    state_path = workspace_root / ".sdd" / "runtime" / "governance-state.json"
    data: dict[str, Any] = {}
    if state_path.exists():
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    _STATE_CACHE[key] = data
    return data


def _store_governance_state(workspace_root: Path, data: dict[str, Any]) -> None:
    """Write `governance-state.json` and refresh the shared in-process cache."""
    state_path = workspace_root / ".sdd" / "runtime" / "governance-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _STATE_CACHE[str(workspace_root.resolve())] = data
