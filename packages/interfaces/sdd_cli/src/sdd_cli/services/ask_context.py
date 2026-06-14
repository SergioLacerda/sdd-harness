"""ask_context — workspace context loading for sdd ask.

Exposes `load_ask_context` as the primary entry point. No Click dependency
in public functions; Click context is accessed only via internal helpers
that guard with `silent=True`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
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


def check_fingerprint_drift(workspace_root: Path, loaded_fingerprint: str) -> bool:
    """Return True if the loaded governance fingerprint differs from the cached state."""
    if not loaded_fingerprint:
        return False
    try:
        state_path = workspace_root / ".sdd" / "runtime" / "governance-state.json"
        if not state_path.exists():
            return False
        data = json.loads(state_path.read_text(encoding="utf-8"))
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
        state_path = workspace_root / ".sdd" / "runtime" / "governance-state.json"
        data: dict[str, Any] = {}
        if state_path.exists():
            try:
                data = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["last_ask"] = last_ask
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as exc:
        logger.debug("Failed to update runtime cache: %s", exc)


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
    )
