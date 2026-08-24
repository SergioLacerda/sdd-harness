"""Workspace context drift checks and last-ask fingerprint cache for `sdd ask`.

Split out of `ask_context.py` (T8,
`.analysis/pending/2026-06-15-sdd-cli-refactoring-pending-followup.md`).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from sdd_cli.services.ask_governance_state_cache import (
    _load_governance_state,
    _store_governance_state,
)

logger = logging.getLogger(__name__)


def check_root_seed_drift(workspace_root: Path) -> bool:
    """Return True if any root seed file's fingerprint header disagrees with metadata.json.

    Structurally distinct from `check_fingerprint_drift` below: this compares
    installed root files (AGENTS.md, CLAUDE.md, GEMINI.md) against source
    metadata, not cached runtime state against the currently loaded fingerprint.
    Intentionally not merged with `check_fingerprint_drift` — see
    `governance_config_reader.check_root_seed_drift` for the underlying check.
    """
    from sdd_cli.services.governance_config_reader import (
        check_root_seed_drift as _check_root_seed_drift_impl,
    )

    ok, _reason = _check_root_seed_drift_impl(str(workspace_root / ".sdd"))
    return not ok


def check_fingerprint_drift(workspace_root: Path, loaded_fingerprint: str) -> bool:
    """Return True if the loaded governance fingerprint differs from the cached state."""
    if not loaded_fingerprint:
        return False
    try:
        data = _load_governance_state(workspace_root)
        if not data:
            return False
        # Prefer last_ask.compiled_fingerprint_used — same kind of hash as loaded_fingerprint.
        # spec_fingerprint is a hash of source files, not compiled output, so comparing
        # loaded_fingerprint against it produces a permanent false-positive.
        last_ask = data.get("last_ask") or {}
        cached_fp = str(last_ask.get("compiled_fingerprint_used", "")).strip()
        if not cached_fp:
            cached_fp = str(data.get("spec_fingerprint", "")).strip()
        if not cached_fp:
            return False
        return loaded_fingerprint[:8] != cached_fp[:8]
    except Exception:
        return False


def write_runtime_cache(workspace_root: Path, last_ask: dict[str, Any]) -> None:
    """Persist last-ask metadata to the runtime governance-state cache."""
    try:
        data = _load_governance_state(workspace_root)
        data["last_ask"] = last_ask
        _store_governance_state(workspace_root, data)
    except Exception as exc:
        logger.debug("Failed to update runtime cache: %s", exc)


def _read_runtime_state(workspace_root: Path) -> dict[str, Any]:
    return _load_governance_state(workspace_root)


def compute_routing_signature(query: str, skill: str | None, fingerprint: str) -> str:
    """Return a stable signature for a routing-decision cache lookup.

    Combines normalized query text, skill selection, and the compiled
    governance fingerprint. The fingerprint alone already reflects the
    combined mandates/registry state (`.sdd/metadata.json` ->
    `fingerprints.combined`), so no separate registry-version component is
    needed for invalidation.
    """
    normalized_query = " ".join(query.strip().lower().split())
    normalized_skill = (skill or "").strip().lower()
    raw = f"{normalized_query}|{normalized_skill}|{fingerprint}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_last_known_fingerprint(workspace_root: Path) -> str:
    """Return the compiled fingerprint recorded by the previous `sdd ask` call, if any."""
    last_ask = _read_runtime_state(workspace_root).get("last_ask") or {}
    return str(last_ask.get("compiled_fingerprint_used", "")).strip()
