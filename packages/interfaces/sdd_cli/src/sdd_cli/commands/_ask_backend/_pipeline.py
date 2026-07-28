"""sdd ask — command entrypoints and governed snapshot builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
from sdd_runtime.cache import get_context_cache

from sdd_cli.commands._ask_backend import app
from sdd_cli.services.ask_organize import run_sdd_organize as run_sdd_organize
from sdd_cli.services.ask_organize import (
    should_use_organize as _should_use_organize,
)
from sdd_cli.utils.output import is_json_mode

from ._helpers import (
    _collect_learning_signals,
    _signature_mode,
)

_HANDBOOK_LOOKUP_LIMIT = 5


def _cached_handbook_lookup(
    root: Path, *, query: str, task_type: str, operation_phase: str
) -> Any:
    """Look up runtime handbook entries via the shared `ContextLoader` cache.

    The default `sdd ask` snapshot path re-read and re-matched
    `index.yaml` on every call with zero caching benefit, unlike `--dossier`
    (which already uses this same in-memory LRU cache, 128 entries/5-min TTL,
    via `ContextLoader`). Reusing that cache here — keyed on the query plus
    task_type/operation_phase — avoids re-parsing the handbook index for a
    repeated/near-identical query within the TTL window.
    """
    from sdd_cli.services.governance_docs_sources import lookup_runtime_handbook

    cache = get_context_cache()
    artifact_id = f"handbook:{root.resolve()}"
    item_types = [task_type, f"phase:{operation_phase}"]
    cached = cache.get(artifact_id, query, _HANDBOOK_LOOKUP_LIMIT, item_types)
    if cached is not None:
        return cached
    result = lookup_runtime_handbook(
        root, task_type=task_type, operation_phase=operation_phase
    )
    cache.set(artifact_id, query, _HANDBOOK_LOOKUP_LIMIT, item_types, result)
    return result


__all__ = [
    "_should_use_organize",
    "ask_cmd",
    "build_governed_ask_snapshot",
    "run_sdd_organize",
]


def _infer_handbook_task_type(query: str, skill: str | None) -> str:
    skill_value = (skill or "").strip().lower()
    if skill_value in {"planning", "implementation", "diagnosis"}:
        return skill_value
    if skill_value in {"diagnose", "debug", "stabilize"}:
        return "diagnosis"
    query_value = query.lower()
    if any(token in query_value for token in ("diagnos", "erro", "error", "fail")):
        return "diagnosis"
    if any(token in query_value for token in ("plan", "design", "proposal")):
        return "planning"
    return "implementation"


def build_governed_ask_snapshot(
    *,
    query: str,
    skill: str | None,
    organize_used: bool,
    workspace_root: Any | None = None,
    require_handshake: bool = True,
    cached_handbook_task_type: str | None = None,
) -> dict[str, Any]:
    """Build a governed ask snapshot with envelope + learning context."""
    from sdd_cli.commands import _ask_backend as _backend

    root = workspace_root or _backend._resolve_workspace_root()
    if require_handshake:
        _backend._guard_handshake(root)
    (
        context_source,
        fingerprint,
        mandates_count,
        authenticated,
        degraded,
        degrade_reason,
        trust_source,
    ) = _backend._load_compiled_governance(root)
    if _signature_mode() == "strict" and not authenticated:
        raise PermissionError(degrade_reason)
    drift_detected = _backend._runtime_drift_check(root, fingerprint)
    root_seed_drift_detected = _backend._root_seed_drift_check(root)
    learning_signals = _collect_learning_signals(workspace_root=root)
    handbook_task_type = (
        cached_handbook_task_type
        if cached_handbook_task_type is not None
        else _infer_handbook_task_type(query, skill)
    )
    handbook_lookup = _cached_handbook_lookup(
        root,
        query=query,
        task_type=handbook_task_type,
        operation_phase="context_loading",
    )
    return {
        "workspace_root": root,
        "context_source": context_source,
        "fingerprint": fingerprint,
        "mandates_count": mandates_count,
        "authenticated": authenticated,
        "degraded": degraded,
        "degrade_reason": degrade_reason,
        "trust_source": trust_source,
        "drift_detected": drift_detected,
        "root_seed_drift_detected": root_seed_drift_detected,
        "learning_signals": learning_signals,
        "handbook_task_type": handbook_task_type,
        "handbook_lookup": {
            "status": handbook_lookup.status,
            "diagnostic": handbook_lookup.diagnostic,
            "matches": handbook_lookup.matches,
        },
    }


# ---------------------------------------------------------------------------
# sdd ask
# ---------------------------------------------------------------------------


@app.command("ask")
def _ask_cli_cmd(
    ctx: typer.Context,
    query: str = typer.Argument(
        ..., help="Governance query (text is hashed, never stored)."
    ),
    dossier: bool = typer.Option(
        False, "--dossier", help="Build comprehensive task dossier with analysis."
    ),
    skill: str | None = typer.Option(  # noqa: UP045
        None, "--skill", help="Skill context (e.g., 'diagnose', 'optimize')."
    ),
    budget: int | None = typer.Option(  # noqa: UP045
        None, "--budget", help="Token budget ceiling for this query."
    ),
    full: bool = typer.Option(
        False, "--full", help="Emit detailed steps and full telemetry payload."
    ),
    log_path: str | None = typer.Option(  # noqa: UP045
        None, "--log-path", help="Custom compliance log path."
    ),
    log_format: str = typer.Option(
        "jsonl", "--log-format", help="Log format: jsonl or compact."
    ),
    tokens_input: int | None = typer.Option(  # noqa: UP045
        None,
        "--tokens-input",
        help="LLM API input tokens (overrides SDD_TOKENS_INPUT).",
    ),
    tokens_output: int | None = typer.Option(  # noqa: UP045
        None,
        "--tokens-output",
        help="LLM API output tokens (overrides SDD_TOKENS_OUTPUT).",
    ),
    intake_only: bool = typer.Option(
        False,
        "--intake-only",
        help="Cheap hook-mode profile: execution_gate/intake_index_mode/intent only.",
    ),
) -> None:
    """Query SDD governance context — minimal governed output."""
    from sdd_cli.commands import _ask_backend as _backend

    token = _backend._JSON_MODE_OVERRIDE.set(is_json_mode(ctx))
    try:
        ask_cmd(
            query=query,
            dossier=dossier,
            skill=skill,
            budget=budget,
            full=full,
            log_path=log_path,
            log_format=log_format,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            intake_only=intake_only,
        )
    finally:
        _backend._JSON_MODE_OVERRIDE.reset(token)


def ask_cmd(
    query: str,
    dossier: bool = False,
    skill: str | None = None,
    budget: int | None = None,
    full: bool = False,
    log_path: str | None = None,
    log_format: str = "jsonl",
    tokens_input: int | None = None,
    tokens_output: int | None = None,
    *,
    intake_only: bool = False,
    output_json: bool | None = None,
) -> None:
    """Query SDD governance context — minimal governed output."""
    from sdd_cli.commands import _ask_backend as _backend

    token = (
        _backend._JSON_MODE_OVERRIDE.set(output_json)
        if output_json is not None
        else None
    )
    try:
        _backend._ask_cmd_impl(
            query=query,
            dossier=dossier,
            skill=skill,
            budget=budget,
            full=full,
            log_path=log_path,
            log_format=log_format,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            intake_only=intake_only,
        )
    finally:
        if token is not None:
            _backend._JSON_MODE_OVERRIDE.reset(token)
