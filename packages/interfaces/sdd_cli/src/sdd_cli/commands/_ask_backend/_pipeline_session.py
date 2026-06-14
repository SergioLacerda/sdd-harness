"""Session and intake helpers for `sdd ask` pipeline."""

from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Any

import typer

from sdd_cli.services.ask_types import _AskInputs, _AskSessionContext

from ._helpers import _json_mode, _now

logger = logging.getLogger(__name__)


def _run_organize_intake(
    workspace_root: Any, query: str
) -> tuple[bool, str, str, int, str]:
    """Run sdd-organize intake and return (used, reason, artifact_path, chunks, retrieval)."""
    from sdd_cli.commands import _ask_backend as _backend

    organize_used, organize_reason = _backend._should_use_organize(query)
    organize_artifact_path = ""
    organize_chunks = 0
    organize_retrieval = "indexed_only"
    if organize_used:
        try:
            organize_artifact, organize_path = _backend.run_sdd_organize(
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
