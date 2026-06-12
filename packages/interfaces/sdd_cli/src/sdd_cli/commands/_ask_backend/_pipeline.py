"""sdd ask — command pipeline entrypoints and session setup helpers."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

import typer

from sdd_cli.commands._ask_backend import app
from sdd_cli.services.ask_organize import run_sdd_organize as run_sdd_organize
from sdd_cli.services.ask_organize import (
    should_use_organize as _should_use_organize,
)
from sdd_cli.services.ask_types import _AskInputs, _AskSessionContext
from sdd_cli.utils.output import is_json_mode

from ._helpers import (
    _collect_learning_signals,
    _json_mode,
    _now,
    _signature_mode,
)

logger = logging.getLogger(__name__)

__all__ = [
    "_emit_state_warnings",
    "_load_ask_snapshot",
    "_run_organize_intake",
    "_should_use_organize",
    "_start_ask_session",
    "ask_cmd",
    "build_governed_ask_snapshot",
    "run_sdd_organize",
]


# ---------------------------------------------------------------------------
# sdd ask — helpers
# ---------------------------------------------------------------------------


def _run_organize_intake(
    workspace_root: Any, query: str
) -> tuple[bool, str, str, int, str]:
    """Run sdd-organize intake and return (used, reason, artifact_path, chunks, retrieval)."""
    organize_used, organize_reason = _should_use_organize(query)
    organize_artifact_path = ""
    organize_chunks = 0
    organize_retrieval = "indexed_only"
    if organize_used:
        try:
            organize_artifact, organize_path = run_sdd_organize(
                workspace_root=workspace_root,
                query=query,
                source_text=query,
                route_reason=organize_reason,
            )
            organize_artifact_path = str(organize_path)
            organize_chunks = len(organize_artifact.get("chunks", []))
            organize_retrieval = str(
                organize_artifact.get("retrieval_policy", "indexed_only")
            )
        except Exception as exc:
            logger.debug("sdd-organize failed in ask: %s", exc)
            organize_retrieval = "degraded"
    return (
        organize_used,
        organize_reason,
        organize_artifact_path,
        organize_chunks,
        organize_retrieval,
    )


def _emit_state_warnings(state: str) -> None:
    if _json_mode():
        return
    if state in ("NOT_INITIALIZED", "MISCONFIGURED"):
        typer.echo(
            f"SOFT [ask]: workspace {state}. Run 'sdd governance compile' before using ask.",
            err=True,
        )
    elif state == "PARTIAL":
        typer.echo(
            "SOFT [ask]: workspace PARTIAL — compiled governance may be stale. "
            "Next: 'sdd governance compile'",
            err=True,
        )


def build_governed_ask_snapshot(
    *,
    query: str,
    skill: str | None,
    organize_used: bool,
    workspace_root: Any | None = None,
    require_handshake: bool = True,
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
    learning_signals = _collect_learning_signals(workspace_root=root)
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
        "learning_signals": learning_signals,
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
        )
    finally:
        if token is not None:
            _backend._JSON_MODE_OVERRIDE.reset(token)


def _start_ask_session(query: str) -> _AskSessionContext:
    from sdd_cli.commands import _ask_backend as _backend

    start_mono = time.monotonic()
    start_ts = _now()
    _backend._guard_budget_breach()
    workspace_root = _backend._resolve_workspace_root()
    (
        organize_used,
        organize_reason,
        organize_artifact_path,
        organize_chunks,
        organize_retrieval,
    ) = _backend._run_organize_intake(workspace_root, query)
    _backend._guard_handshake(workspace_root)
    profile, state = _backend._get_profile_state()
    _backend._emit_state_warnings(state)
    return _AskSessionContext(
        workspace_root=workspace_root,
        organize_used=organize_used,
        organize_reason=organize_reason,
        organize_artifact_path=organize_artifact_path,
        organize_chunks=organize_chunks,
        organize_retrieval=organize_retrieval,
        profile=profile,
        state=state,
        agent_id=os.environ.get("SDD_AGENT_ID", "unknown"),
        trace_id=str(uuid.uuid4()),
        start_mono=start_mono,
        start_ts=start_ts,
    )


def _load_ask_snapshot(
    inputs: _AskInputs, session: _AskSessionContext
) -> dict[str, Any]:
    from sdd_cli.commands import _ask_backend as _backend

    try:
        return _backend.build_governed_ask_snapshot(
            query=inputs.query,
            skill=inputs.skill,
            organize_used=session.organize_used,
            workspace_root=session.workspace_root,
            require_handshake=True,
        )
    except PermissionError as exc:
        typer.echo(f"BLOCK [ask]: {exc}", err=True)
        raise typer.Exit(3) from None
