"""Presentation and exit helpers for governance command handlers."""

from __future__ import annotations

from typing import Any

import typer
from rich.console import Console

from sdd_cli.services.governance_artifact_handlers import (
    render_governance_compile_table,
)
from sdd_cli.shared.contracts import build_error_result
from sdd_cli.utils.output import emit_json
from sdd_core.output.canonical_event import CanonicalLogEvent


def handle_compile_output(
    *,
    output_json: bool,
    payload: dict[str, Any],
    is_error: bool,
    phase_1: dict[str, Any],
    phase_2: dict[str, Any],
    core_fingerprint: str,
    consistency_reason: str,
    console: Console,
    artifact_path: str = "",
) -> None:
    """Emit compile output and raise standardized exit when failed."""
    if output_json:
        emit_json(payload, err=is_error)
        if is_error:
            raise typer.Exit(1)
        return

    if is_error:
        event = CanonicalLogEvent(
            level="error",
            phase="compile",
            event_type="artifact_consistency_failed",
            summary=consistency_reason,
            decision="blocked",
            artifact_path=artifact_path,
            next_action="sdd governance validate",
        )
        console.print(f"[red]{event.simple_output()}[/red]")
        raise typer.Exit(1)

    render_governance_compile_table(
        console=console,
        phase_1=phase_1,
        phase_2=phase_2,
        core_fingerprint=core_fingerprint,
    )
    console.print("[green]Governance compilation succeeded[/green]")


def fail_generate_precondition(
    *,
    output_json: bool,
    code: str,
    message: str,
    data: dict[str, Any],
    console: Console,
) -> None:
    """Emit standardized generate precondition error and exit 1."""
    if output_json:
        emit_json(
            build_error_result(
                "governance generate",
                code=code,
                message=message,
                data=data,
            ),
            err=True,
        )
    else:
        event = CanonicalLogEvent(
            level="error",
            phase="generate",
            event_type=code,
            summary=message,
            decision="blocked",
            artifact_path=str(data.get("resolved_path", "")),
        )
        console.print(f"[red]{event.simple_output()}[/red]")
    raise typer.Exit(1)
