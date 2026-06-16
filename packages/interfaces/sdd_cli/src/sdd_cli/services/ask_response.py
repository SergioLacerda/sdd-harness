"""ask_response — final text response emission for `sdd ask`.

Dossier helpers are injected as callables since they are thin wrappers
owned by `commands/_ask_backend.py`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import typer

from sdd_cli.services.ask_types import _AskInputs, _AskSessionContext


def _now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:8]


def emit_ask_text_response(
    inputs: _AskInputs,
    session: _AskSessionContext,
    ask_snapshot: dict[str, Any],
    output_text: str,
    governance_footer: str,
    *,
    build_and_output_dossier_fn: Callable[..., None],
) -> None:
    """Echo the plain-text response and footer for `sdd ask` to stdout."""
    mandates_count = ask_snapshot["mandates_count"]
    typer.echo(output_text)
    intake_mode = "multi" if session.organize_used else "none"
    gate_blocked = (
        not session.organize_used and session.organize_reason != "light_input"
    )
    gate = "blocked" if gate_blocked else "allowed"
    gate_suffix = (
        ""
        if gate == "allowed"
        else "\ngate_reason       : intake_index_mode=none"
        f"\nintake_skipped    : {session.organize_reason} (query {len(inputs.query)} chars"
        " < 6000; pass ≥6000 chars or use: sdd-organize --input-file <path> <query>)"
    )
    typer.echo(
        f"intake_index_mode : {intake_mode}\n"
        f"intake_chunks     : {session.organize_chunks}\n"
        f"intake_retrieval  : {session.organize_retrieval}\n"
        f"intake_artifact   : {session.organize_artifact_path or 'n/a'}\n"
        f"governance_mode   : hard\n"
        f"execution_gate    : {gate}"
        f"{gate_suffix}"
    )
    if inputs.dossier:
        build_and_output_dossier_fn(
            query=inputs.query,
            skill=inputs.skill,
            budget=inputs.budget,
            mandates_count=mandates_count,
            workspace_root=session.workspace_root,
        )
    typer.echo(governance_footer)
