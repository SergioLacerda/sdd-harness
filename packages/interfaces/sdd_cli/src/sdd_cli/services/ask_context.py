"""Workspace context loading for sdd ask — primary entry point: `load_ask_context`."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sdd_cli.services.ask_governance import GovResult
from sdd_cli.services.ask_governance import (
    load_compiled_governance as _load_compiled_governance_impl,
)
from sdd_cli.services.ask_governance import (
    load_governance_via_runtime as _load_governance_via_runtime,
)
from sdd_cli.utils.sdd_authority import (
    compiled_active_dir,
    enforce_path_policy,
    profile_active_path,
)
from sdd_cli.utils.sdd_authority import (
    resolve_workspace_root as _resolve_authority_workspace_root,
)

logger = logging.getLogger(__name__)

_GOV_CACHE: dict[str, GovResult] = {}

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


@dataclass(frozen=True)
class AskContext:
    """Resolved workspace context for a single ask invocation."""

    workspace_root: Path
    profile: str
    ahp_state: str
    context_source: str
    fingerprint: str
    mandates_count: int
    authenticated: bool
    degraded: bool
    degrade_reason: str
    trust_source: str
    drift_detected: bool
    root_seed_drift_detected: bool


class WorkspaceNotFoundError(Exception):
    """Raised when the SDD workspace root cannot be resolved."""


def resolve_workspace_root() -> Path:
    """Resolve and validate the SDD workspace root path."""
    root = _resolve_authority_workspace_root()
    return enforce_path_policy(root, workspace_root=root, mode="normal")


def get_cached_ahp() -> dict[str, Any] | None:
    """Return the AHP result cached in the current Click context, if available."""
    try:
        import click

        ctx = click.get_current_context(silent=True)
        if ctx is not None and isinstance(ctx.obj, dict):
            cached = ctx.obj.get("_ahp")
            if isinstance(cached, dict):
                return cached
    except (ImportError, RuntimeError):
        return None
    return None


def get_profile_state(workspace_root: Path) -> tuple[str, str]:
    """Return (profile, state) best-effort; never raises."""
    profile = ""
    profile_path = profile_active_path(workspace_root)
    if profile_path.exists():
        try:
            import configparser

            parser = configparser.ConfigParser()
            parser.read(profile_path)
            profile = parser.get("sdd", "type", fallback="").strip()
        except Exception:
            profile = ""
    cached_ahp = get_cached_ahp()
    if cached_ahp is not None:
        return profile or "default", str(cached_ahp.get("state", "UNKNOWN"))
    try:
        from sdd_core.governance.handshake import AgentHandshakeProtocol

        ahp = AgentHandshakeProtocol(project_root=workspace_root)
        state, _ = ahp.validate(output_mode="silent")
        return profile or "default", state
    except Exception:
        return profile or "default", "UNKNOWN"


def load_compiled_governance(workspace_root: Path) -> GovResult:
    """Load compiled governance config from cache or disk."""
    key = str(workspace_root.resolve())
    cached = _GOV_CACHE.get(key)
    if cached is not None:
        return cached
    result = _load_compiled_governance_impl(
        workspace_root,
        compiled_active_dir_fn=compiled_active_dir,
        logger=logger,
        load_via_runtime_fn=_load_governance_via_runtime,
    )
    _GOV_CACHE[key] = result
    return result


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


_ROUTING_CACHE_MAX_ENTRIES = 20


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


_SNAPSHOT_CACHE_MAX_ENTRIES = 20
_SNAPSHOT_CACHE_TTL_SECONDS = 300


def get_cached_governance_snapshot(
    workspace_root: Path, fingerprint: str
) -> dict[str, Any] | None:
    """Return a cached compiled-governance snapshot for `fingerprint`, if still fresh.

    Keyed by fingerprint only — the cached fields (`context_source`,
    `mandates_count`, `authenticated`, `degraded`, `degrade_reason`,
    `trust_source`) are a pure function of the compiled governance state for a
    given fingerprint, mirroring the in-process `_GOV_CACHE` but persisted to
    disk so it survives across separate `sdd ask` processes (design.md D-A).

    Bounded by a TTL (mirroring `ContextLoader`'s own 5-minute TTL) rather than
    relying on fingerprint match alone: the lookup fingerprint here is the
    *last-known* one recorded in `governance-state.json`, not a freshly
    reloaded one — skipping the real compiled-governance load on every hit
    means a recompile would otherwise never be detected. The TTL bounds how
    long a cache hit can go without forcing a fresh load, so staleness after a
    recompile is capped at `_SNAPSHOT_CACHE_TTL_SECONDS`, not unbounded.
    """
    if not fingerprint:
        return None
    entry = (
        _load_governance_state(workspace_root)
        .get("snapshot_cache", {})
        .get(fingerprint)
    )
    if not isinstance(entry, dict):
        return None
    computed_at = entry.get("computed_at")
    if not computed_at:
        return None
    try:
        computed_dt = datetime.fromisoformat(str(computed_at).replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - computed_dt).total_seconds()
    except (ValueError, TypeError):
        return None
    if age_seconds > _SNAPSHOT_CACHE_TTL_SECONDS:
        return None
    snapshot = entry.get("snapshot")
    return snapshot if isinstance(snapshot, dict) else None


def store_governance_snapshot(
    workspace_root: Path, fingerprint: str, snapshot: dict[str, Any]
) -> None:
    """Persist a compiled-governance snapshot, capped to the most recent entries."""
    if not fingerprint:
        return
    try:
        data = _load_governance_state(workspace_root)
        entries = data.get("snapshot_cache")
        if not isinstance(entries, dict):
            entries = {}
        entries[fingerprint] = {
            "snapshot": snapshot,
            "computed_at": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        }
        if len(entries) > _SNAPSHOT_CACHE_MAX_ENTRIES:
            ordered = sorted(
                entries.items(),
                key=lambda item: item[1].get("computed_at", ""),
                reverse=True,
            )
            entries = dict(ordered[:_SNAPSHOT_CACHE_MAX_ENTRIES])
        data["snapshot_cache"] = entries
        _store_governance_state(workspace_root, data)
    except Exception as exc:
        logger.debug("Failed to update governance snapshot cache: %s", exc)


def get_cached_routing_decision(
    workspace_root: Path, signature: str
) -> dict[str, Any] | None:
    """Return a previously cached routing decision for `signature`, if present."""
    decisions = _read_runtime_state(workspace_root).get("last_routing_decisions") or {}
    cached = decisions.get(signature)
    return cached if isinstance(cached, dict) else None


def resolve_routing_decision(
    workspace_root: Path, query: str, skill: str | None
) -> dict[str, Any] | None:
    """Return a cached routing decision for `query`/`skill`, if one applies.

    Keyed by the fingerprint recorded by the previous `sdd ask` call. Returns
    None on cold start (no prior call recorded), so a decision is never
    cached against an empty/unknown fingerprint — the first call for a
    workspace always runs the routing heuristics for real.

    Reads `governance-state.json` once (not via `get_last_known_fingerprint`
    + `get_cached_routing_decision` separately, which would each re-read the
    file) — design.md D4 flags redundant reads of this file as an
    inefficiency to avoid, and this lookup previously did two on every call.
    """
    state = _read_runtime_state(workspace_root)
    last_ask = state.get("last_ask") or {}
    fingerprint = str(last_ask.get("compiled_fingerprint_used", "")).strip()
    if not fingerprint:
        return None
    signature = compute_routing_signature(query, skill, fingerprint)
    decisions = state.get("last_routing_decisions") or {}
    cached = decisions.get(signature)
    return cached if isinstance(cached, dict) else None


def store_routing_decision(
    workspace_root: Path,
    query: str,
    skill: str | None,
    fingerprint: str,
    decision: dict[str, Any],
) -> None:
    """Persist a routing decision, capped to the most recent entries.

    Keyed by the fingerprint actually loaded for this call (not the
    last-known one used for lookup), so the cache self-heals on the next
    call after a governance change instead of perpetuating a stale entry.
    """
    if not fingerprint:
        return
    signature = compute_routing_signature(query, skill, fingerprint)
    try:
        data = _load_governance_state(workspace_root)
        decisions = data.get("last_routing_decisions")
        if not isinstance(decisions, dict):
            decisions = {}
        decisions[signature] = {
            **decision,
            "computed_at": datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        }
        if len(decisions) > _ROUTING_CACHE_MAX_ENTRIES:
            ordered = sorted(
                decisions.items(),
                key=lambda item: item[1].get("computed_at", ""),
                reverse=True,
            )
            decisions = dict(ordered[:_ROUTING_CACHE_MAX_ENTRIES])
        data["last_routing_decisions"] = decisions
        _store_governance_state(workspace_root, data)
    except Exception as exc:
        logger.debug("Failed to update routing decision cache: %s", exc)


def write_runtime_cache_and_routing_decision(
    workspace_root: Path,
    last_ask: dict[str, Any],
    query: str,
    skill: str | None,
    fingerprint: str,
    routing_decision: dict[str, Any],
    governance_snapshot: dict[str, Any] | None = None,
) -> None:
    """Persist `last_ask`, a routing decision, and a governance snapshot in one write.

    `write_runtime_cache` + `store_routing_decision` always run back-to-back
    at the end of a `sdd ask` call and each independently reads/writes
    `governance-state.json` — two reads and two writes for state that is
    always updated together. This combines them into one read + one write
    (design.md D4). `write_runtime_cache` and `store_routing_decision` are
    kept as-is for other callers/tests — they now share the same
    per-process `_load_governance_state`/`_store_governance_state` cache
    (design.md D-01), so calling them elsewhere in the same process no
    longer reintroduces a redundant disk read either.

    `governance_snapshot`, when supplied, is persisted under `snapshot_cache`
    the same way `store_governance_snapshot` does standalone (design.md D-A) —
    folded into this same write rather than opening a third read/write path.
    """
    try:
        data = _load_governance_state(workspace_root)
        data["last_ask"] = last_ask
        if fingerprint:
            signature = compute_routing_signature(query, skill, fingerprint)
            decisions = data.get("last_routing_decisions")
            if not isinstance(decisions, dict):
                decisions = {}
            decisions[signature] = {
                **routing_decision,
                "computed_at": datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),
            }
            if len(decisions) > _ROUTING_CACHE_MAX_ENTRIES:
                ordered = sorted(
                    decisions.items(),
                    key=lambda item: item[1].get("computed_at", ""),
                    reverse=True,
                )
                decisions = dict(ordered[:_ROUTING_CACHE_MAX_ENTRIES])
            data["last_routing_decisions"] = decisions
            if governance_snapshot is not None:
                snapshots = data.get("snapshot_cache")
                if not isinstance(snapshots, dict):
                    snapshots = {}
                snapshots[fingerprint] = {
                    "snapshot": governance_snapshot,
                    "computed_at": datetime.now(timezone.utc)
                    .isoformat(timespec="seconds")
                    .replace("+00:00", "Z"),
                }
                if len(snapshots) > _SNAPSHOT_CACHE_MAX_ENTRIES:
                    ordered_snapshots = sorted(
                        snapshots.items(),
                        key=lambda item: item[1].get("computed_at", ""),
                        reverse=True,
                    )
                    snapshots = dict(ordered_snapshots[:_SNAPSHOT_CACHE_MAX_ENTRIES])
                data["snapshot_cache"] = snapshots
        _store_governance_state(workspace_root, data)
    except Exception as exc:
        logger.debug("Failed to update runtime cache/routing decision: %s", exc)


def load_ask_context(
    workspace_root: Path | None = None, profile: str | None = None
) -> AskContext:
    """Load and return the complete workspace context for an ask invocation.

    Raises WorkspaceNotFoundError if the workspace root does not exist.
    """
    root = workspace_root or resolve_workspace_root()
    if not root.exists():
        raise WorkspaceNotFoundError(f"Workspace root not found: {root}")

    resolved_profile, ahp_state = get_profile_state(root)
    effective_profile = profile or resolved_profile

    (
        context_source,
        fingerprint,
        mandates_count,
        authenticated,
        degraded,
        degrade_reason,
        trust_source,
    ) = load_compiled_governance(root)

    drift_detected = check_fingerprint_drift(root, fingerprint)
    root_seed_drift_detected = check_root_seed_drift(root)

    return AskContext(
        workspace_root=root,
        profile=effective_profile,
        ahp_state=ahp_state,
        context_source=context_source,
        fingerprint=fingerprint,
        mandates_count=mandates_count,
        authenticated=authenticated,
        degraded=degraded,
        degrade_reason=degrade_reason,
        trust_source=trust_source,
        drift_detected=drift_detected,
        root_seed_drift_detected=root_seed_drift_detected,
    )
