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
) -> None:
    """Emit compile output and raise standardized exit when failed."""
    if output_json:
        emit_json(payload, err=is_error)
        if is_error:
            raise typer.Exit(1)
        return

    if is_error:
        console.print("[red]ERROR: Artifact consistency failed after compile[/red]")
        console.print(f"[yellow]{consistency_reason}[/yellow]")
        console.print("  Next: run 'sdd governance validate' for detailed checks")
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
        console.print(f"[red]ERROR: {message}[/red]")
    raise typer.Exit(1)
