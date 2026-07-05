"""Internal helpers for the ``sdd ask`` command pipeline."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from typer.models import OptionInfo

from sdd_cli.services.ask_context import (
    check_fingerprint_drift as _check_fingerprint_drift,
)
from sdd_cli.services.ask_context import (
    check_root_seed_drift as _check_root_seed_drift,
)
from sdd_cli.services.ask_context import get_profile_state as _get_profile_state_impl
from sdd_cli.services.ask_context import (
    load_compiled_governance as _load_compiled_governance,
)
from sdd_cli.services.ask_context import (
    resolve_workspace_root as _resolve_workspace_root,
)
from sdd_cli.services.ask_context import (
    write_runtime_cache as _write_runtime_cache,
)
from sdd_cli.services.ask_filter import (
    collect_learning_signals as _collect_learning_signals_impl,
)
from sdd_cli.services.ask_filter import (
    count_signals_from_tail as _count_signals_from_tail_impl,
)
from sdd_cli.services.ask_governance import signature_mode as _signature_mode_impl
from sdd_cli.services.ask_governance import (
    try_sdd_compiled_dir as _try_sdd_compiled_dir_impl,
)
from sdd_cli.services.ask_renderer import (
    render_context_header as _render_context_header,
)
from sdd_cli.services.ask_renderer import (
    render_governance_footer as _render_governance_footer_impl,
)
from sdd_cli.shared.constants import LEARNING_WINDOW_DAYS as _LEARNING_WINDOW_DAYS
from sdd_cli.shared.constants import TRUE_VALUES as _TRUE_VALUES
from sdd_cli.utils.output import is_json_mode

__all__ = [
    "_check_fingerprint_drift",
    "_load_compiled_governance",
    "_resolve_workspace_root",
    "_write_runtime_cache",
]

logger = logging.getLogger(__name__)


def _now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:8]


def _normalize_typer_value(value: Any, default: Any) -> Any:
    """Normalize Typer OptionInfo leakage when command functions are called directly."""
    return default if isinstance(value, OptionInfo) else value


def _prefer_full_summary() -> bool:
    """Return whether ask context rendering should prefer summary_full."""
    raw = os.environ.get("SDD_ASK_PREFER_FULL_SUMMARY", "")
    return raw.strip().lower() in _TRUE_VALUES


def _try_sdd_compiled_dir(sdd_compiled: Path) -> tuple[str, str, int] | None:
    return _try_sdd_compiled_dir_impl(sdd_compiled, logger=logger)


def _signature_mode() -> str:
    return _signature_mode_impl()


def _get_cached_ahp() -> dict[str, Any] | None:
    ctx = click.get_current_context(silent=True)
    if ctx is not None and isinstance(ctx.obj, dict):
        cached = ctx.obj.get("_ahp")
        if isinstance(cached, dict):
            return cached
    return None


def _get_profile_state() -> tuple[str, str]:
    """Return (profile, state) best-effort; never raises."""
    from sdd_cli.commands import _ask_backend as _backend

    return _get_profile_state_impl(_backend._resolve_workspace_root())


def _runtime_drift_check(workspace_root: Path, loaded_fingerprint: str) -> bool:
    return _check_fingerprint_drift(workspace_root, loaded_fingerprint)


def _root_seed_drift_check(workspace_root: Path) -> bool:
    return _check_root_seed_drift(workspace_root)


def _resolve_ask_drift_type(*, drift_detected: bool, authenticated: bool) -> str:
    """Classify ask drift for telemetry consumers."""
    if not drift_detected:
        return "none"
    if not authenticated:
        return "auth_drift"
    return "fingerprint_drift"


def _resolve_ask_degraded_reason(
    *, degraded: bool, degrade_reason: str, authenticated: bool
) -> str:
    """Provide stable degraded reason when none is explicitly available."""
    if degrade_reason.strip():
        return degrade_reason.strip()
    if degraded and not authenticated:
        return "artifact_unverified"
    if degraded:
        return "degraded_unspecified"
    return ""


def _render_context_output(
    fingerprint: str,
    mandates_count: int,
    *,
    degraded: bool,
    degrade_reason: str,
) -> str:
    return _render_context_header(
        fingerprint,
        mandates_count,
        degraded=degraded,
        degrade_reason=degrade_reason,
    )


def _governance_footer_for_state(
    *,
    state: str,
    profile: str,
    drift_detected: bool,
    root_seed_drift_detected: bool | None = None,
) -> str:
    return _render_governance_footer_impl(
        state=state,
        profile=profile,
        drift_detected=drift_detected,
        root_seed_drift_detected=root_seed_drift_detected,
    )


def _json_mode() -> bool:
    from sdd_cli.commands._ask_backend import _JSON_MODE_OVERRIDE

    override = _JSON_MODE_OVERRIDE.get()
    if override is not None:
        return override
    ctx = click.get_current_context(silent=True)
    while ctx is not None:
        if is_json_mode(ctx):
            return True
        ctx = ctx.parent
    return False


def _count_signals_from_tail(
    path: Path, signals: dict[str, int], cutoff_ts: float, *, from_failures: bool
) -> None:
    _count_signals_from_tail_impl(path, signals, cutoff_ts, from_failures=from_failures)


def _collect_learning_signals(
    workspace_root: Path, *, window_days: int = _LEARNING_WINDOW_DAYS
) -> dict[str, int]:
    return _collect_learning_signals_impl(workspace_root, window_days=window_days)
